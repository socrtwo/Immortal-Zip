# CLAUDE.md

A dual-implementation ZIP/unzip tool that can repair corrupt archives by
scanning for `PK\x03\x04` local file headers and inflating each entry
independently. **Two implementations live side-by-side and stay
interoperable** — touching one without considering the other is the most
common way to break things.

## Repo map

- `immortal_zip/` — Python implementation (CLI + Tk GUI). The canonical
  recovery engine.
- `web/` — JS/PWA implementation: `immortal-inflate.js`,
  `immortal-unzip.js`, plus the Immortal Unzip page (`immortal-unzip.html`
  at repo root is the standalone entry).
- `windows/`, `macos/`, `linux/`, `chromeos/`, `android/`, `ios/` —
  per-platform Electron / native shells wrapping the JS implementation.
- `tests/` — recovery + interop tests. Run these before pushing.
- `lib/`, `build/` — shared helpers and build outputs.
- `pyproject.toml` — Python packaging config.
- `.github/workflows/` — `pages.yml` (Pages deploy on push to `main`),
  `release.yml` (build per-platform installers on `v*` tag).

## Branch policy

Work on the assigned feature branch:

1. Commit and push the feature branch.
2. **Open a PR from the feature branch to `main`** using the GitHub MCP
   tools (`mcp__github__create_pull_request`). Do not merge directly —
   the maintainer reviews and merges.
3. Pages and Release pipelines fire only after the PR lands on `main`.

## Releasing

- Tag a `v*` commit on `main` (or use Actions → Release →
  workflow_dispatch) to produce Windows `Setup.exe`, macOS `.dmg`, Linux
  `.deb` / `.AppImage`, plus the PWA bundle.
- The Android APK and (signed) iOS IPA are wrapped from the PWA — keep
  the PWA build green or every mobile artifact breaks.

## Verifying changes

- Python: `python -m pytest tests/` (or `pytest` if installed).
- JS/PWA: open `immortal-unzip.html` locally and exercise unzip + repair
  on a known-corrupt fixture from `tests/`.
- **Interop check:** if you change the inflate logic in *either*
  implementation, run a repair on the same fixture with both and confirm
  identical entry counts and byte lengths.

## Gotchas

- The recovery strategy is shared by spec, not by code. A fix in
  `immortal_zip/` must be mirrored in `web/immortal-inflate.js` (or
  vice-versa) or the two implementations diverge silently.
- `PK\x03\x04` scanning must keep working when the central directory is
  missing — don't add code paths that require a valid EOCD.
- The PWA cache version in `web/service-worker.js` (if present) needs a
  bump whenever you change cached assets, or users keep seeing stale
  code.
