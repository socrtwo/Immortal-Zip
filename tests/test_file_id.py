"""Tests for immortal_zip.file_id — magic-number identification and
embedded/concatenated-file segmentation (mirrors web/s2-file-id.js)."""

from __future__ import annotations

import io
import zipfile

from immortal_zip import file_id


def make_zip(names_and_data: dict[str, bytes] | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in (names_and_data or {"hello.txt": b"hello world" * 20}).items():
            zf.writestr(name, data)
    return buf.getvalue()


def make_pdf() -> bytes:
    return (
        b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
        + b"stream data " * 40
        + b"\ntrailer\n<<>>\n%%EOF\n"
    )


def make_ole_xls() -> bytes:
    """OLE2 magic + a UTF-16LE 'Workbook' stream name, padded to 512-byte sectors."""
    body = (
        b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
        + b"\x00" * 120
        + "Workbook".encode("utf-16-le")
        + b"\x00" * 200
    )
    pad = (-len(body)) % 512
    return body + b"\x00" * pad


# --------------------------------------------------------------------------
# Identification
# --------------------------------------------------------------------------

def test_identify_plain_zip() -> None:
    info = file_id.identify(make_zip())
    assert info.ext == "zip"
    assert info.confidence == "high"


def test_identify_xlsx_by_entry_names() -> None:
    data = make_zip({
        "[Content_Types].xml": b"<Types/>",
        "xl/workbook.xml": b"<workbook/>",
    })
    assert file_id.identify(data).ext == "xlsx"


def test_identify_pdf() -> None:
    assert file_id.identify(make_pdf()).ext == "pdf"


def test_identify_ole_workbook_as_xls() -> None:
    info = file_id.identify(make_ole_xls())
    assert info.ext == "xls"


def test_identify_plain_text() -> None:
    assert file_id.identify(b"just some ordinary text\nwith lines\n").ext == "txt"


# --------------------------------------------------------------------------
# Segmentation
# --------------------------------------------------------------------------

def test_single_zip_is_one_segment() -> None:
    data = make_zip()
    segments = file_id.scan(data)
    assert len(segments) == 1
    assert segments[0].ext == "zip"
    assert segments[0].data == data


def test_zip_plus_pdf_concatenated() -> None:
    zip_bytes = make_zip()
    pdf_bytes = make_pdf()
    data = zip_bytes + pdf_bytes

    segments = file_id.scan(data)
    assert len(segments) == 2
    assert [s.ext for s in segments] == ["zip", "pdf"]
    assert segments[0].data == zip_bytes
    assert segments[1].data == pdf_bytes
    assert segments[1].offset == len(zip_bytes)


def test_pdf_plus_zip_concatenated() -> None:
    pdf_bytes = make_pdf()
    zip_bytes = make_zip()
    data = pdf_bytes + zip_bytes

    segments = file_id.scan(data)
    assert len(segments) == 2
    assert [s.ext for s in segments] == ["pdf", "zip"]
    assert segments[1].data == zip_bytes


def test_ole_then_zip_respects_512_alignment() -> None:
    ole = make_ole_xls()
    assert len(ole) % 512 == 0
    zip_bytes = make_zip()
    segments = file_id.scan(ole + zip_bytes)
    assert [s.ext for s in segments] == ["xls", "zip"]
    assert segments[1].offset == len(ole)


# --------------------------------------------------------------------------
# analyze() — the host-program entry point
# --------------------------------------------------------------------------

def test_analyze_zip_no_mismatch() -> None:
    data = make_zip()
    report = file_id.analyze(data, program_key="immortalzip", file_name="a.zip")
    assert report.primary.ext == "zip"
    assert not report.mismatch
    assert not report.multiple
    assert report.foreign == []
    assert report.proceed_bytes == data


def test_analyze_zip_plus_pdf_separates_foreign() -> None:
    zip_bytes = make_zip()
    pdf_bytes = make_pdf()
    report = file_id.analyze(
        zip_bytes + pdf_bytes, program_key="immortalzip", file_name="fused.zip"
    )
    assert report.primary.ext == "zip"
    assert not report.mismatch
    assert report.multiple
    assert len(report.foreign) == 1
    foreign = report.foreign[0]
    assert foreign.ext == "pdf"
    assert foreign.data == pdf_bytes
    assert foreign.suggested_name == "fused.part2.pdf"
    assert foreign.recommended, "foreign segment must carry a recommendation"
    assert all(r["key"] != "immortalzip" for r in foreign.recommended)
    # Repair must operate on the zip piece only:
    assert report.proceed_bytes == zip_bytes


def test_analyze_pdf_plus_zip_proceeds_with_zip_segment() -> None:
    pdf_bytes = make_pdf()
    zip_bytes = make_zip()
    report = file_id.analyze(
        pdf_bytes + zip_bytes, program_key="immortalzip", file_name="fused.pdf"
    )
    # Primary (segment 0) is a PDF -> mismatch for a zip tool...
    assert report.primary.ext == "pdf"
    assert report.mismatch
    # ...but the repairable bytes are the zip segment.
    assert report.proceed_segment.ext == "zip"
    assert report.proceed_bytes == zip_bytes


def test_analyze_ole_workbook_mismatch_recommends_excel_tool() -> None:
    report = file_id.analyze(
        make_ole_xls(), program_key="immortalzip", file_name="book.xls"
    )
    assert report.primary.ext == "xls"
    assert report.mismatch
    assert len(report.foreign) == 1
    rec_keys = [r["key"] for r in report.foreign[0].recommended]
    assert rec_keys[0] == "corruptexcelrec"


def test_recommend_excludes_self_and_falls_back_to_universal() -> None:
    assert all(p["key"] != "immortalzip" for p in file_id.recommend("zip", "immortalzip"))
    assert file_id.recommend("pst")[0]["key"] == "universal"
