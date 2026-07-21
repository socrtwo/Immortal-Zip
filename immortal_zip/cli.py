"""Command-line interface for Immortal-Zip."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, file_id
from .core import ZipError, ZipTool


def _print_progress(msg: str, done: int, total: int) -> None:
    if total <= 0:
        return
    pct = (done / total) * 100 if total else 0
    sys.stderr.write(f"\r[{done}/{total} {pct:5.1f}%] {msg[:60]:<60}")
    sys.stderr.flush()
    if done >= total:
        sys.stderr.write("\n")


def cmd_zip(args: argparse.Namespace) -> int:
    tool = ZipTool(progress=_print_progress if not args.quiet else None)
    out = tool.create(args.sources, args.output, compresslevel=args.level)
    print(f"Created: {out}")
    return 0


def cmd_unzip(args: argparse.Namespace) -> int:
    tool = ZipTool(progress=_print_progress if not args.quiet else None)
    dest = tool.extract(args.archive, args.destination)
    print(f"Extracted to: {dest}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    tool = ZipTool()
    for info in tool.list_contents(args.archive):
        print(f"{info.file_size:>12}  {info.date_time}  {info.filename}")
    return 0


def cmd_test(args: argparse.Namespace) -> int:
    tool = ZipTool()
    bad = tool.test(args.archive)
    if bad is None:
        print("OK")
        return 0
    print(f"Corrupted member: {bad}", file=sys.stderr)
    return 2


def cmd_repair(args: argparse.Namespace) -> int:
    tool = ZipTool(progress=_print_progress if not args.quiet else None)

    # First analysis step: identify the file from its magic numbers and
    # separate any embedded/concatenated foreign files before repairing.
    arc_path = Path(args.archive)
    out_path = (
        Path(args.output)
        if args.output is not None
        else arc_path.with_name(arc_path.stem + ".repaired.zip")
    )
    repair_data: bytes | None = None
    try:
        data = arc_path.read_bytes()
    except OSError:
        data = None
    if data is not None:
        report = file_id.analyze(
            data, program_key="immortalzip", file_name=arc_path.name
        )
        print(f"Identified as: {report.primary.description}")
        if report.mismatch:
            recs = file_id.recommend(report.primary.ext)
            print(
                "Warning: this does not look like a ZIP-family file."
                + (f" Recommended tool: {recs[0]['name']} <{recs[0]['url']}>" if recs else "")
            )
        if report.foreign:
            print(
                f"Found {len(report.foreign)} segment(s) of a type this program "
                "does not handle; writing them out before repair:"
            )
            for seg in report.foreign:
                part_path = out_path.with_name(
                    f"{out_path.stem}.part{seg.index + 1}.{seg.ext}"
                )
                part_path.parent.mkdir(parents=True, exist_ok=True)
                part_path.write_bytes(seg.data)
                rec = seg.recommended[0] if seg.recommended else None
                print(f"  - {part_path.name}: {seg.description} ({seg.length} bytes at offset {seg.offset})")
                if rec:
                    print(f"    Repair it with: {rec['name']} <{rec['url']}>")
        if len(report.proceed_bytes) != len(data):
            print(
                f"Proceeding to repair the {len(report.proceed_bytes)}-byte ZIP "
                f"segment at offset {report.proceed_segment.offset}."
            )
            repair_data = report.proceed_bytes

    result = tool.repair(args.archive, args.output, data=repair_data)
    print(f"Repaired archive written to: {result.output}")
    print(f"Recovered: {result.recovered_count} members")
    if result.skipped:
        print(f"Skipped: {result.skipped_count} members (use --verbose for details)")
        if args.verbose:
            for name, reason in result.skipped:
                print(f"  - {name}: {reason}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="immortal-zip",
        description="Zip, unzip, and repair zip archives.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_zip = sub.add_parser("zip", help="Create a zip archive")
    p_zip.add_argument("output", help="Output .zip path")
    p_zip.add_argument("sources", nargs="+", help="Files or directories to add")
    p_zip.add_argument("--level", type=int, default=None, help="Compression level 0-9")
    p_zip.add_argument("--quiet", action="store_true")
    p_zip.set_defaults(func=cmd_zip)

    p_unzip = sub.add_parser("unzip", help="Extract a zip archive")
    p_unzip.add_argument("archive", help="Path to .zip")
    p_unzip.add_argument(
        "destination", nargs="?", default=".", help="Destination directory"
    )
    p_unzip.add_argument("--quiet", action="store_true")
    p_unzip.set_defaults(func=cmd_unzip)

    p_list = sub.add_parser("list", help="List archive contents")
    p_list.add_argument("archive")
    p_list.set_defaults(func=cmd_list)

    p_test = sub.add_parser("test", help="Verify archive integrity")
    p_test.add_argument("archive")
    p_test.set_defaults(func=cmd_test)

    p_repair = sub.add_parser("repair", help="Repair a corrupted zip archive")
    p_repair.add_argument("archive")
    p_repair.add_argument(
        "-o", "--output", default=None, help="Repaired output path (default: <name>.repaired.zip)"
    )
    p_repair.add_argument("--verbose", action="store_true", help="List skipped members")
    p_repair.add_argument("--quiet", action="store_true")
    p_repair.set_defaults(func=cmd_repair)

    p_gui = sub.add_parser("gui", help="Launch graphical interface")
    p_gui.set_defaults(func=lambda _a: _launch_gui())

    return parser


def _launch_gui() -> int:
    from .gui import run

    run()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ZipError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"Error: file not found: {exc.filename}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
