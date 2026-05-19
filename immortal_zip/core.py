"""Core zip/unzip/repair engine for Immortal-Zip.

Repair strategy:
- A valid ZIP ends with an End-Of-Central-Directory (EOCD) record (signature
  PK\\x05\\x06). The Central Directory (CD) describes every member.
- When the CD/EOCD is missing or corrupted, the archive cannot be opened by
  normal tooling, even though the per-file Local File Headers (LFH, signature
  PK\\x03\\x04) typically remain readable.
- Repair scans the raw bytes for LFH signatures, recovers each member's
  compressed data, and writes a new, well-formed ZIP with a fresh CD/EOCD.
"""

from __future__ import annotations

import os
import struct
import zipfile
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

LFH_SIG = b"PK\x03\x04"
CFH_SIG = b"PK\x01\x02"
EOCD_SIG = b"PK\x05\x06"
DATA_DESC_SIG = b"PK\x07\x08"


class ZipError(Exception):
    """Raised for unrecoverable zip operations."""


@dataclass
class RepairResult:
    source: Path
    output: Path
    recovered: list[str] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)
    rebuilt_central_directory: bool = False

    @property
    def recovered_count(self) -> int:
        return len(self.recovered)

    @property
    def skipped_count(self) -> int:
        return len(self.skipped)


ProgressFn = Callable[[str, int, int], None]


def _noop_progress(_msg: str, _done: int, _total: int) -> None:
    return None


class ZipTool:
    """High-level operations for zipping, unzipping, and repairing archives."""

    def __init__(self, progress: ProgressFn | None = None) -> None:
        self.progress = progress or _noop_progress

    def create(
        self,
        sources: Iterable[str | os.PathLike[str]],
        output: str | os.PathLike[str],
        compression: int = zipfile.ZIP_DEFLATED,
        compresslevel: int | None = None,
    ) -> Path:
        """Create a new zip archive from one or more files/directories."""
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        files: list[tuple[Path, str]] = []
        for src in sources:
            src_path = Path(src)
            if not src_path.exists():
                raise ZipError(f"Source not found: {src_path}")
            if src_path.is_dir():
                base = src_path.parent
                for child in sorted(src_path.rglob("*")):
                    if child.is_file():
                        files.append((child, str(child.relative_to(base))))
            else:
                files.append((src_path, src_path.name))

        total = len(files)
        self.progress("create", 0, total)
        with zipfile.ZipFile(
            out_path, "w", compression=compression, compresslevel=compresslevel
        ) as zf:
            for idx, (path, arcname) in enumerate(files, start=1):
                zf.write(path, arcname)
                self.progress(f"add:{arcname}", idx, total)
        return out_path

    def extract(
        self,
        archive: str | os.PathLike[str],
        destination: str | os.PathLike[str],
        members: Iterable[str] | None = None,
        password: bytes | None = None,
    ) -> Path:
        """Extract a zip archive to a destination directory."""
        arc_path = Path(archive)
        dest_path = Path(destination)
        dest_path.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(arc_path, "r") as zf:
            names = list(members) if members is not None else zf.namelist()
            total = len(names)
            self.progress("extract", 0, total)
            for idx, name in enumerate(names, start=1):
                self._safe_extract(zf, name, dest_path, password)
                self.progress(f"extract:{name}", idx, total)
        return dest_path

    def list_contents(self, archive: str | os.PathLike[str]) -> list[zipfile.ZipInfo]:
        with zipfile.ZipFile(Path(archive), "r") as zf:
            return zf.infolist()

    def test(self, archive: str | os.PathLike[str]) -> str | None:
        """Verify CRCs. Returns the first bad member name, or None on success."""
        try:
            with zipfile.ZipFile(Path(archive), "r") as zf:
                return zf.testzip()
        except zipfile.BadZipFile as exc:
            raise ZipError(f"Not a valid zip archive: {exc}") from exc

    def repair(
        self,
        archive: str | os.PathLike[str],
        output: str | os.PathLike[str] | None = None,
    ) -> RepairResult:
        """Repair a corrupted zip by salvaging every readable member."""
        arc_path = Path(archive)
        if not arc_path.is_file():
            raise ZipError(f"Archive not found: {arc_path}")

        out_path = (
            Path(output)
            if output is not None
            else arc_path.with_name(arc_path.stem + ".repaired.zip")
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)

        data = arc_path.read_bytes()
        result = RepairResult(source=arc_path, output=out_path)
        result.rebuilt_central_directory = True

        entries = list(self._iter_local_headers(data))
        total = len(entries)
        self.progress("repair-scan", total, total)
        if total == 0:
            raise ZipError(
                "No recoverable entries found — file does not appear to contain "
                "zip data."
            )

        with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for idx, entry in enumerate(entries, start=1):
                name = entry["name"]
                try:
                    payload = self._extract_member_payload(data, entry)
                    if name.endswith("/"):
                        info = zipfile.ZipInfo(name)
                        info.external_attr = (0o755 << 16) | 0x10
                        zf.writestr(info, b"")
                    else:
                        zf.writestr(name, payload)
                    result.recovered.append(name)
                    self.progress(f"repair:{name}", idx, total)
                except Exception as exc:  # noqa: BLE001 — repair must be forgiving
                    result.skipped.append((name, str(exc)))
                    self.progress(f"skip:{name}", idx, total)

        if not result.recovered:
            try:
                out_path.unlink()
            except OSError:
                pass
            raise ZipError(
                "Repair failed — no members could be recovered from the archive."
            )
        return result

    def _safe_extract(
        self,
        zf: zipfile.ZipFile,
        name: str,
        dest: Path,
        password: bytes | None,
    ) -> None:
        target = (dest / name).resolve()
        if not str(target).startswith(str(dest.resolve())):
            raise ZipError(f"Refusing to extract outside destination: {name}")
        zf.extract(name, dest, pwd=password)

    def _iter_local_headers(self, data: bytes):
        offset = 0
        size = len(data)
        while True:
            idx = data.find(LFH_SIG, offset)
            if idx < 0:
                return
            header_end = idx + 30
            if header_end > size:
                return
            (
                _sig,
                version,
                flags,
                method,
                mtime,
                mdate,
                crc32,
                comp_size,
                uncomp_size,
                name_len,
                extra_len,
            ) = struct.unpack("<4sHHHHHIIIHH", data[idx:header_end])
            name_start = header_end
            name_end = name_start + name_len
            extra_end = name_end + extra_len
            if extra_end > size:
                return
            raw_name = data[name_start:name_end]
            try:
                name = raw_name.decode("utf-8")
            except UnicodeDecodeError:
                name = raw_name.decode("latin-1", errors="replace")

            entry = {
                "lfh_offset": idx,
                "data_offset": extra_end,
                "name": name,
                "method": method,
                "flags": flags,
                "crc32": crc32,
                "comp_size": comp_size,
                "uncomp_size": uncomp_size,
                "mtime": mtime,
                "mdate": mdate,
            }
            yield entry
            offset = extra_end + max(comp_size, 0) if comp_size > 0 else extra_end + 1

    def _extract_member_payload(self, data: bytes, entry: dict) -> bytes:
        start = entry["data_offset"]
        method = entry["method"]
        comp_size = entry["comp_size"]
        flags = entry["flags"]

        if comp_size == 0 and (flags & 0x08):
            comp_data = self._scan_until_next_header(data, start)
        elif comp_size > 0:
            comp_data = data[start : start + comp_size]
        else:
            comp_data = self._scan_until_next_header(data, start)

        if method == zipfile.ZIP_STORED:
            return comp_data
        if method == zipfile.ZIP_DEFLATED:
            decompressor = zlib.decompressobj(-zlib.MAX_WBITS)
            try:
                return decompressor.decompress(comp_data) + decompressor.flush()
            except zlib.error:
                decompressor = zlib.decompressobj(-zlib.MAX_WBITS)
                chunk_size = 4096
                out = bytearray()
                pos = 0
                while pos < len(comp_data):
                    try:
                        out += decompressor.decompress(comp_data[pos : pos + chunk_size])
                    except zlib.error:
                        break
                    pos += chunk_size
                try:
                    out += decompressor.flush()
                except zlib.error:
                    pass
                if not out:
                    raise
                return bytes(out)
        raise ZipError(f"Unsupported compression method {method} for {entry['name']}")

    def _scan_until_next_header(self, data: bytes, start: int) -> bytes:
        candidates = []
        for sig in (LFH_SIG, CFH_SIG, EOCD_SIG, DATA_DESC_SIG):
            idx = data.find(sig, start)
            if idx >= 0:
                candidates.append(idx)
        end = min(candidates) if candidates else len(data)
        return data[start:end]
