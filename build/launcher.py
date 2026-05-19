"""Entry point for the bundled GUI executable.

If launched with CLI arguments, falls through to the command-line interface.
"""

import sys


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] not in ("gui",):
        from immortal_zip.cli import main as cli_main
        return cli_main()
    from immortal_zip.gui import run
    run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
