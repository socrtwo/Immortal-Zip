"""End-to-end tests for the zip/unzip/repair pipeline."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from immortal_zip.core import ZipError, ZipTool


@pytest.fixture()
def sample_tree(tmp_path: Path) -> Path:
    src = tmp_path / "src"
    (src / "sub").mkdir(parents=True)
    (src / "hello.txt").write_text("hello world")
    (src / "sub" / "nested.txt").write_text("nested file" * 50)
    (src / "binary.bin").write_bytes(bytes(range(256)) * 4)
    return src


def test_create_and_extract_roundtrip(tmp_path: Path, sample_tree: Path) -> None:
    tool = ZipTool()
    archive = tmp_path / "out.zip"
    tool.create([sample_tree], archive)
    assert archive.exists() and archive.stat().st_size > 0

    dest = tmp_path / "extracted"
    tool.extract(archive, dest)

    assert (dest / "src" / "hello.txt").read_text() == "hello world"
    assert (dest / "src" / "sub" / "nested.txt").read_text() == "nested file" * 50
    assert (dest / "src" / "binary.bin").read_bytes() == bytes(range(256)) * 4


def test_test_returns_none_for_good_archive(tmp_path: Path, sample_tree: Path) -> None:
    tool = ZipTool()
    archive = tmp_path / "ok.zip"
    tool.create([sample_tree], archive)
    assert tool.test(archive) is None


def test_repair_recovers_from_missing_eocd(tmp_path: Path, sample_tree: Path) -> None:
    tool = ZipTool()
    archive = tmp_path / "good.zip"
    tool.create([sample_tree], archive)

    raw = archive.read_bytes()
    eocd_idx = raw.rfind(b"PK\x05\x06")
    cd_idx = raw.find(b"PK\x01\x02")
    assert eocd_idx > 0 and cd_idx > 0

    truncated = raw[:cd_idx] + b"GARBAGE\x00\x00\x00" * 4
    corrupted = tmp_path / "corrupt.zip"
    corrupted.write_bytes(truncated)

    with pytest.raises(zipfile.BadZipFile):
        with zipfile.ZipFile(corrupted) as zf:
            zf.namelist()

    result = tool.repair(corrupted)
    assert result.recovered_count >= 3
    assert result.output.exists()

    with zipfile.ZipFile(result.output) as zf:
        assert zf.testzip() is None
        names = set(zf.namelist())
    assert any(n.endswith("hello.txt") for n in names)
    assert any(n.endswith("nested.txt") for n in names)


def test_repair_recovers_when_eocd_is_garbage(tmp_path: Path, sample_tree: Path) -> None:
    tool = ZipTool()
    archive = tmp_path / "good.zip"
    tool.create([sample_tree], archive)

    raw = bytearray(archive.read_bytes())
    eocd_idx = raw.rfind(b"PK\x05\x06")
    for i in range(4):
        raw[eocd_idx + i] = 0xFF
    corrupted = tmp_path / "bad-eocd.zip"
    corrupted.write_bytes(bytes(raw))

    result = tool.repair(corrupted)
    assert result.recovered_count >= 3
    with zipfile.ZipFile(result.output) as zf:
        assert zf.testzip() is None


def test_repair_fails_on_non_zip_data(tmp_path: Path) -> None:
    junk = tmp_path / "not-a-zip.zip"
    junk.write_bytes(b"this is plain text, not a zip file")
    tool = ZipTool()
    with pytest.raises(ZipError):
        tool.repair(junk)


def test_extract_rejects_path_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "evil.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../escape.txt", "pwned")
    archive.write_bytes(buf.getvalue())

    tool = ZipTool()
    with pytest.raises(ZipError):
        tool.extract(archive, tmp_path / "out")
