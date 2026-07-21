"""S2 File Identifier — shared first-step analysis for the S2 recovery suite.

This module is a faithful Python port of ``web/s2-file-id.js`` and the two
MUST stay in sync: any change to the identification, segmentation, or
program-recommendation logic in either file must be mirrored in the other
(the S2 suite shares this behaviour by spec, not by code).

Before any repair runs, this module:

1. Reads the file's magic numbers and identifies what kind of file it is
   (ZIP refined to docx/xlsx/pptx/ODF/epub/jar/apk via raw entry-name
   search; OLE2 refined to doc/xls/ppt/msg via UTF-16LE stream names;
   plus PDF, images, RTF, 7z, RAR, gzip, SQLite, text heuristics, ...).
2. Scans the whole buffer for additional embedded / concatenated files
   (e.g. a PDF glued onto a ZIP by a disk error) and separates them into
   segments.  The ZIP local-header walk is only trusted end-to-end when
   it reaches the EOCD; otherwise only the verified prefix is guarded.
3. Maps each "foreign" segment (a type this program does not handle) to
   the best other program in the S2 tool suite.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re

# --------------------------------------------------------------------------
# Program registry — the S2 tool suite and what each program handles.
# Mirrors PROGRAMS in web/s2-file-id.js.
# --------------------------------------------------------------------------

PROGRAMS: list[dict] = [
    {"key": "universal",         "name": "Universal File Repair Tool",            "url": "https://socrtwo.github.io/Universal-File-Repair-Tool/", "handles": ["*"]},
    {"key": "corruptdocxrepair", "name": "CorruptDOCXRepair",                     "url": "https://socrtwo.github.io/CorruptDOCXRepair/",          "handles": ["docx"]},
    {"key": "quickwordrecovr",   "name": "Quick Word Recovr",                     "url": "https://socrtwo.github.io/quickwordrecovr-SF/",         "handles": ["docx"]},
    {"key": "wordrecovery",      "name": "Word Recovery",                         "url": "https://socrtwo.github.io/wordrecovery-SF/",            "handles": ["doc", "docx"]},
    {"key": "damageddocx2txt",   "name": "Damageddocx2txt",                       "url": "https://socrtwo.github.io/damageddocx2txt-SF/",         "handles": ["docx"]},
    {"key": "corruptexcelrec",   "name": "S2 Recovery Tools for Microsoft Excel", "url": "https://socrtwo.github.io/corruptexcelrec-SF/",         "handles": ["xls", "xlsx"]},
    {"key": "excelrcvryaddin",   "name": "Excel Recovery Addin",                  "url": "https://socrtwo.github.io/excelrcvryaddin-SF/",         "handles": ["xls"]},
    {"key": "pptxrecovery",      "name": "PPTX Recovery",                         "url": "https://socrtwo.github.io/pptxrecovery-SF/",            "handles": ["pptx"]},
    {"key": "oorecovery",        "name": "OO Recovery (OpenDocument)",            "url": "https://socrtwo.github.io/oorecovery-SF/",              "handles": ["odt", "ods", "odp", "odg"]},
    {"key": "immortalzip",       "name": "Immortal Zip",                          "url": "https://socrtwo.github.io/Immortal-Zip/",               "handles": ["zip", "jar", "apk", "epub"]},
    {"key": "xmltrncatorfixr",   "name": "XML Truncator-Fixer",                   "url": "https://socrtwo.github.io/xmltrncatorfixr-SF/app/",     "handles": ["xml", "docx", "xlsx", "pptx"]},
    {"key": "savvyoffice",       "name": "Savvy Repair for Microsoft Office",     "url": "https://socrtwo.github.io/savvyoffice-SF/",             "handles": ["doc", "xls", "ppt", "docx", "xlsx", "pptx"]},
    {"key": "coffice2txt",       "name": "Coffice2txt",                           "url": "https://socrtwo.github.io/coffice2txt-SF/",             "handles": ["doc", "xls", "ppt", "docx", "xlsx", "pptx"]},
    {"key": "crrptoffcxtrctr",   "name": "Crrptoffcxtrctr (Office extractor)",    "url": "https://socrtwo.github.io/crrptoffcxtrctr-SF/",         "handles": ["docx", "xlsx", "pptx"]},
    {"key": "saveofficedata",    "name": "Saveofficedata",                        "url": "https://socrtwo.github.io/saveofficedata-SF/",          "handles": ["doc", "xls", "ppt"]},
    {"key": "filefixerbot",      "name": "File Fixer Bot",                        "url": "https://socrtwo.github.io/file-fixer-bot/",             "handles": ["*"]},
    {"key": "datarecoverfree",   "name": "Datarecoverfree",                       "url": "https://socrtwo.github.io/datarecoverfree-SF/",         "handles": []},
    {"key": "vistaprevrsrcvr",   "name": "Previous Version Explorer",             "url": "https://socrtwo.github.io/vistaprevrsrcvr-SF/",         "handles": []},
]

# Preferred repair order per detected extension (best tool first).
RECOMMEND_ORDER: dict[str, list[str]] = {
    "docx": ["corruptdocxrepair", "quickwordrecovr", "wordrecovery", "xmltrncatorfixr", "savvyoffice", "crrptoffcxtrctr", "damageddocx2txt", "coffice2txt"],
    "doc":  ["wordrecovery", "savvyoffice", "coffice2txt", "saveofficedata"],
    "xls":  ["corruptexcelrec", "savvyoffice", "excelrcvryaddin", "coffice2txt", "saveofficedata"],
    "xlsx": ["corruptexcelrec", "xmltrncatorfixr", "savvyoffice", "crrptoffcxtrctr", "coffice2txt"],
    "ppt":  ["savvyoffice", "coffice2txt", "saveofficedata"],
    "pptx": ["pptxrecovery", "xmltrncatorfixr", "savvyoffice", "crrptoffcxtrctr", "coffice2txt"],
    "odt":  ["oorecovery"], "ods": ["oorecovery"], "odp": ["oorecovery"], "odg": ["oorecovery"],
    "zip":  ["immortalzip"], "jar": ["immortalzip"], "apk": ["immortalzip"], "epub": ["immortalzip"],
    "xml":  ["xmltrncatorfixr"],
}


def program_by_key(key: str) -> dict | None:
    for p in PROGRAMS:
        if p["key"] == key:
            return p
    return None


def recommend(ext: str, exclude_key: str | None = None) -> list[dict]:
    """Ordered suite programs that can repair ``ext``, excluding ``exclude_key``.

    Falls back to the universal tool when nothing specific matches.
    """
    out = []
    for key in RECOMMEND_ORDER.get(ext, []):
        if key == exclude_key:
            continue
        p = program_by_key(key)
        if p:
            out.append(p)
    if not out and exclude_key != "universal":
        out.append(program_by_key("universal"))
    return out


def program_handles(program_key: str, ext: str) -> bool:
    p = program_by_key(program_key)
    if not p:
        return False
    return "*" in p["handles"] or ext in p["handles"]


# --------------------------------------------------------------------------
# Signatures
# --------------------------------------------------------------------------

SIG = {
    "ZIP_LOCAL": b"PK\x03\x04",
    "ZIP_EOCD":  b"PK\x05\x06",
    "ZIP_CDIR":  b"PK\x01\x02",
    "ZIP_SPAN":  b"PK\x07\x08",
    "OLE2":      b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",
    "PDF":       b"%PDF-",
    "PNG":       b"\x89PNG\r\n\x1a\n",
    "GIF87":     b"GIF87a",
    "GIF89":     b"GIF89a",
    "JPEG":      b"\xff\xd8\xff",
    "RTF":       b"{\\rtf",
    "SEVENZ":    b"7z\xbc\xaf\x27\x1c",
    "RAR":       b"Rar!\x1a\x07",
    "GZIP":      b"\x1f\x8b\x08",
    "XMLDECL":   b"<?xml",
    "TIFF_LE":   b"II*\x00",
    "TIFF_BE":   b"MM\x00*",
    "SQLITE":    b"SQLite f",
    "RIFF":      b"RIFF",
    "OGG":       b"OggS",
    "FLAC":      b"fLaC",
    "ID3":       b"ID3",
    "PST":       b"!BDN",
}

DESCRIPTIONS = {
    "docx": "Microsoft Word document (DOCX, Office Open XML)",
    "xlsx": "Microsoft Excel workbook (XLSX, Office Open XML)",
    "pptx": "Microsoft PowerPoint presentation (PPTX, Office Open XML)",
    "ooxml": "Microsoft Office Open XML document (type unclear)",
    "doc":  "Microsoft Word 97-2003 document (DOC)",
    "xls":  "Microsoft Excel 97-2003 workbook (XLS)",
    "ppt":  "Microsoft PowerPoint 97-2003 presentation (PPT)",
    "msg":  "Microsoft Outlook message (MSG)",
    "vsd":  "Microsoft Visio drawing (VSD)",
    "ole":  "Microsoft Office compound (OLE2) file — exact type unclear",
    "odt":  "OpenDocument text (ODT)",
    "ods":  "OpenDocument spreadsheet (ODS)",
    "odp":  "OpenDocument presentation (ODP)",
    "odg":  "OpenDocument drawing (ODG)",
    "epub": "EPUB e-book",
    "jar":  "Java archive (JAR)",
    "apk":  "Android package (APK)",
    "zip":  "ZIP archive",
    "pdf":  "PDF document",
    "png":  "PNG image",
    "gif":  "GIF image",
    "jpg":  "JPEG image",
    "tif":  "TIFF image",
    "bmp":  "BMP image",
    "rtf":  "Rich Text Format document (RTF)",
    "7z":   "7-Zip archive",
    "rar":  "RAR archive",
    "gz":   "GZIP compressed data",
    "xml":  "XML document",
    "html": "HTML document",
    "sqlite": "SQLite database",
    "pst":  "Outlook data file (PST/OST)",
    "wav":  "WAV audio", "avi": "AVI video", "webp": "WebP image",
    "ogg":  "OGG media", "flac": "FLAC audio", "mp3": "MP3 audio",
    "mp4":  "MP4 / QuickTime media",
    "exe":  "Windows executable (EXE/DLL)",
    "txt":  "Plain text",
    "csv":  "Comma-separated values (CSV)",
    "bin":  "Unrecognized binary data",
}


def _u16le(b: bytes, o: int) -> int:
    return b[o] | (b[o + 1] << 8)


def _u32le(b: bytes, o: int) -> int:
    return b[o] | (b[o + 1] << 8) | (b[o + 2] << 16) | (b[o + 3] << 24)


def _matches(b: bytes, off: int, sig: bytes) -> bool:
    return b[off:off + len(sig)] == sig and off + len(sig) <= len(b)


def _utf16le(s: str) -> bytes:
    return s.encode("utf-16-le")


# --------------------------------------------------------------------------
# ZIP refinement
# --------------------------------------------------------------------------

def _refine_zip(b: bytes, start: int, end: int) -> str:
    """Distinguish DOCX / XLSX / PPTX / ODF / EPUB / JAR / APK / plain ZIP.

    Uses raw byte search for well-known entry names — this keeps working
    when the archive structure itself is corrupt, because entry names are
    stored uncompressed in local headers and the central directory.
    """
    def has(s: str) -> bool:
        return b.find(s.encode("latin-1"), start, end) != -1

    if has("mimetypeapplication/vnd.oasis.opendocument.text"):
        return "odt"
    if has("mimetypeapplication/vnd.oasis.opendocument.spreadsheet"):
        return "ods"
    if has("mimetypeapplication/vnd.oasis.opendocument.presentation"):
        return "odp"
    if has("mimetypeapplication/vnd.oasis.opendocument.graphics"):
        return "odg"
    if has("mimetypeapplication/epub+zip"):
        return "epub"
    is_ooxml = has("[Content_Types].xml")
    if has("word/document.xml") or has("word/_rels/"):
        return "docx"
    if has("xl/workbook.xml") or has("xl/_rels/"):
        return "xlsx"
    if has("ppt/presentation.xml") or has("ppt/slides/"):
        return "pptx"
    if is_ooxml:
        return "ooxml"
    if has("AndroidManifest.xml"):
        return "apk"
    if has("META-INF/MANIFEST.MF"):
        return "jar"
    # ODF whose mimetype entry was compressed or lost:
    if has("content.xml") and has("META-INF/manifest.xml"):
        if has("office:spreadsheet"):
            return "ods"
        if has("office:presentation"):
            return "odp"
        return "odt"
    return "zip"


def _walk_zip_entries(b: bytes, start: int) -> tuple[int, bool]:
    """Best-effort walk of ZIP local file headers starting at ``start``.

    Returns ``(end, clean)`` where ``end`` is the last offset proven to be
    inside this archive's entry data (so signature hits below it are
    internal, not a second file) and ``clean`` says the walk never broke.
    Only a walk that reaches the EOCD is trusted end-to-end; otherwise only
    the verified prefix is guarded — appended foreign files are then still
    found even when a truncated entry's declared size would swallow them.
    """
    pos = start
    verified = start
    n = len(b)
    while pos + 30 <= n and _matches(b, pos, SIG["ZIP_LOCAL"]):
        verified = pos
        flags = _u16le(b, pos + 6)
        csize = _u32le(b, pos + 18)
        name_len = _u16le(b, pos + 26)
        extra_len = _u16le(b, pos + 28)
        data_start = pos + 30 + name_len + extra_len
        if name_len == 0 or data_start > n:
            break
        verified = data_start
        if flags & 0x08:
            # Data descriptor: sizes unknown up front — find the next
            # descriptor signature; if absent the walk cannot continue.
            dd = b.find(SIG["ZIP_SPAN"], data_start)
            if dd == -1:
                pos = data_start
                break
            pos = dd + 16
        else:
            nxt = data_start + csize
            if nxt > n:
                pos = data_start
                break
            pos = nxt
    # Central directory + EOCD follow the entries.
    if _matches(b, pos, SIG["ZIP_CDIR"]):
        verified = pos
    while pos + 46 <= n and _matches(b, pos, SIG["ZIP_CDIR"]):
        cn = _u16le(b, pos + 28)
        ce = _u16le(b, pos + 30)
        cc = _u16le(b, pos + 32)
        pos = pos + 46 + cn + ce + cc
    if pos + 22 <= n and _matches(b, pos, SIG["ZIP_EOCD"]):
        comment = _u16le(b, pos + 20)
        return min(pos + 22 + comment, n), True
    return min(verified, n), False


# --------------------------------------------------------------------------
# OLE2 refinement
# --------------------------------------------------------------------------

def _refine_ole(b: bytes, start: int, end: int) -> str:
    def has16(s: str) -> bool:
        return b.find(_utf16le(s), start, end) != -1

    if has16("WordDocument"):
        return "doc"
    if has16("Workbook") or has16("Book"):
        return "xls"
    if has16("PowerPoint Document"):
        return "ppt"
    if has16("VisioDocument"):
        return "vsd"
    if has16("__properties_version1.0") or has16("__recip_version1.0"):
        return "msg"
    return "ole"


# --------------------------------------------------------------------------
# Identification
# --------------------------------------------------------------------------

def _looks_like_text(b: bytes, start: int, end: int) -> bool:
    n = min(end - start, 4096)
    if n == 0:
        return False
    printable = 0
    for i in range(n):
        c = b[start + i]
        if c in (9, 10, 13) or 32 <= c < 127 or c >= 128:
            printable += 1
        elif c == 0:
            return False
    return printable / n > 0.95


@dataclass
class Identification:
    ext: str
    description: str
    confidence: str = "high"


def identify_at(b: bytes, start: int = 0, end: int | None = None) -> Identification:
    """Identify the file that starts at ``start`` (default 0)."""
    if end is None:
        end = len(b)

    def res(ext: str, confidence: str = "high") -> Identification:
        return Identification(ext, DESCRIPTIONS.get(ext, ext), confidence)

    if _matches(b, start, SIG["ZIP_LOCAL"]) or _matches(b, start, SIG["ZIP_EOCD"]):
        return res(_refine_zip(b, start, end))
    if _matches(b, start, SIG["OLE2"]):
        return res(_refine_ole(b, start, end))
    if _matches(b, start, SIG["PDF"]):
        return res("pdf")
    if _matches(b, start, SIG["PNG"]):
        return res("png")
    if _matches(b, start, SIG["GIF87"]) or _matches(b, start, SIG["GIF89"]):
        return res("gif")
    if _matches(b, start, SIG["JPEG"]):
        return res("jpg")
    if _matches(b, start, SIG["RTF"]):
        return res("rtf")
    if _matches(b, start, SIG["SEVENZ"]):
        return res("7z")
    if _matches(b, start, SIG["RAR"]):
        return res("rar")
    if _matches(b, start, SIG["GZIP"]):
        return res("gz")
    if _matches(b, start, SIG["SQLITE"]):
        return res("sqlite")
    if _matches(b, start, SIG["PST"]):
        return res("pst")
    if _matches(b, start, SIG["TIFF_LE"]) or _matches(b, start, SIG["TIFF_BE"]):
        return res("tif")
    if _matches(b, start, SIG["OGG"]):
        return res("ogg")
    if _matches(b, start, SIG["FLAC"]):
        return res("flac")
    if _matches(b, start, SIG["ID3"]):
        return res("mp3", "medium")
    if _matches(b, start, SIG["RIFF"]):
        if _matches(b, start + 8, b"WAVE"):
            return res("wav")
        if _matches(b, start + 8, b"AVI "):
            return res("avi")
        if _matches(b, start + 8, b"WEBP"):
            return res("webp")
        return res("bin", "low")
    if _matches(b, start + 4, b"ftyp"):
        return res("mp4")
    if start + 1 < len(b) and b[start] == 0x4D and b[start + 1] == 0x5A:
        return res("exe", "medium")
    if start + 1 < len(b) and b[start] == 0x42 and b[start + 1] == 0x4D and start == 0:
        return res("bmp", "medium")
    if _matches(b, start, SIG["XMLDECL"]):
        # <?xml ... — could be plain XML or a Flat ODF / saved OOXML part.
        return res("xml")
    if _looks_like_text(b, start, end):
        head = b[start:min(end, start + 512)].decode("latin-1")
        lower = head.lower()
        if "<!doctype html" in lower or "<html" in lower:
            return res("html")
        if "<?xml" in lower or re.match(r"^\s*<", head):
            return res("xml", "medium")
        return res("txt", "medium")
    return res("bin", "low")


def identify(b: bytes) -> Identification:
    return identify_at(b, 0)


# --------------------------------------------------------------------------
# Embedded / concatenated file scan
# --------------------------------------------------------------------------

# Signatures strong enough to mark the start of a NEW file mid-buffer.
BOUNDARY_SIGS: list[tuple[str, bytes]] = [
    ("zip", SIG["ZIP_LOCAL"]),
    ("ole", SIG["OLE2"]),
    ("pdf", SIG["PDF"]),
    ("png", SIG["PNG"]),
    ("gif", SIG["GIF87"]), ("gif", SIG["GIF89"]),
    # JPEG start-of-image plus a plausible first marker (4 bytes) — the bare
    # 3-byte SOI is too easy to hit inside compressed data.
    ("jpg", b"\xff\xd8\xff\xe0"), ("jpg", b"\xff\xd8\xff\xe1"),
    ("jpg", b"\xff\xd8\xff\xdb"), ("jpg", b"\xff\xd8\xff\xee"),
    ("jpg", b"\xff\xd8\xff\xc0"), ("jpg", b"\xff\xd8\xff\xe2"),
    ("rtf", SIG["RTF"]),
    ("7z", SIG["SEVENZ"]),
    ("rar", SIG["RAR"]),
    ("sqlite", SIG["SQLITE"]),
    ("pst", SIG["PST"]),
]


def _seg_state(b: bytes, start: int) -> dict:
    """Per-segment scan state: how far the file starting at ``start`` provably
    extends (``guard``), and which acceptance rules apply inside it."""
    if _matches(b, start, SIG["ZIP_LOCAL"]):
        end, clean = _walk_zip_entries(b, start)
        return {"start": start, "kind": "zip", "walk_clean": clean, "guard": max(start + 4, end)}
    if _matches(b, start, SIG["OLE2"]):
        return {"start": start, "kind": "ole", "guard": start + 512}
    if _matches(b, start, SIG["JPEG"]):
        return {"start": start, "kind": "jpg", "guard": start + 4}
    return {"start": start, "kind": "other", "guard": start + 1}


@dataclass
class Segment:
    index: int
    offset: int
    length: int
    ext: str
    description: str
    confidence: str
    data: bytes
    handled_here: bool = True
    suggested_name: str = ""
    recommended: list = field(default_factory=list)


def scan(b: bytes) -> list[Segment]:
    """Scan the buffer and split it into segments, one per distinct file.

    Heuristic by design: it never destroys data — segments are offered as
    extra outputs, and segment 0 is always the file the host program was
    asked to repair.
    """
    seg_starts = [0]
    cur = _seg_state(b, 0)
    pos = max(1, cur["guard"])
    n = len(b)

    while pos < n:
        hit = None
        for ext, sig in BOUNDARY_SIGS:
            if _matches(b, pos, sig):
                hit = (ext, sig)
                break
        if hit:
            hit_ext, hit_sig = hit
            accept = True
            if cur["kind"] == "zip":
                if hit_ext == "zip":
                    # A PK header inside a zip we could not walk cleanly is
                    # almost always a member of the SAME corrupt archive.
                    accept = cur["walk_clean"]
                else:
                    # Inside a corrupt zip, short signatures are likely
                    # deflate noise; demand 5+ signature bytes.
                    accept = cur["walk_clean"] or len(hit_sig) >= 5
            elif cur["kind"] == "ole":
                # A file concatenated after an OLE2 doc always lands on a
                # 512-byte boundary (OLE size is a multiple of 512).
                aligned = (pos - cur["start"]) % 512 == 0
                accept = aligned or len(hit_sig) >= 6
            elif cur["kind"] == "jpg" and hit_ext == "jpg":
                # Embedded EXIF thumbnails also start with SOI — only split
                # if an end-of-image marker was seen before this point.
                accept = b.find(b"\xff\xd9", cur["start"], pos) != -1
            if accept:
                seg_starts.append(pos)
                cur = _seg_state(b, pos)
                pos = max(pos + 1, cur["guard"])
                continue
        pos += 1

    segments = []
    for i, start in enumerate(seg_starts):
        end = seg_starts[i + 1] if i + 1 < len(seg_starts) else n
        info = identify_at(b, start, end)
        segments.append(Segment(
            index=i,
            offset=start,
            length=end - start,
            ext=info.ext,
            description=info.description,
            confidence=info.confidence,
            data=b[start:end],
        ))
    return segments


# --------------------------------------------------------------------------
# Analyze — the one call host programs make first
# --------------------------------------------------------------------------

@dataclass
class Report:
    file_name: str
    primary: Identification
    segments: list[Segment]
    matching: list[Segment]
    foreign: list[Segment]
    multiple: bool
    mismatch: bool
    proceed_bytes: bytes
    proceed_segment: Segment


def analyze(data: bytes, program_key: str | None = None,
            file_name: str = "recovered-file") -> Report:
    """Identify ``data``, separate concatenated/embedded files, and decide
    which bytes the host program should actually repair.

    Mirrors ``S2FileID.analyze()`` in ``web/s2-file-id.js``.
    """
    base = re.sub(r"\.[A-Za-z0-9]{1,6}$", "", file_name)
    segments = scan(data)
    matching: list[Segment] = []
    foreign: list[Segment] = []

    for i, seg in enumerate(segments):
        handled = program_handles(program_key, seg.ext) if program_key else True
        seg.handled_here = handled
        seg.suggested_name = (
            f"{base}.part{i + 1}.{seg.ext}" if len(segments) > 1 else f"{base}.{seg.ext}"
        )
        if handled:
            matching.append(seg)
        else:
            seg.recommended = recommend(seg.ext, program_key)
            foreign.append(seg)

    proceed = matching[0] if matching else segments[0]
    return Report(
        file_name=file_name,
        primary=Identification(segments[0].ext, segments[0].description, segments[0].confidence),
        segments=segments,
        matching=matching,
        foreign=foreign,
        multiple=len(segments) > 1,
        mismatch=(not program_handles(program_key, segments[0].ext)) if program_key else False,
        proceed_bytes=proceed.data if proceed else data,
        proceed_segment=proceed,
    )
