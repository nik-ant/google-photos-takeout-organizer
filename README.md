<div align="center">

# Google Photos Takeout Organizer

Organize a Google Photos Takeout export into a chronological library while preserving albums.

[Quick start](#quick-start) · [Output](#output) · [Documentation](#documentation)

</div>

The Python script reads Takeout folders or ZIP archives and copies supported media into a new folder. It uses Takeout sidecar dates when available, with embedded media timestamps as a fallback. Original files are left untouched.

## Highlights

- Builds a year-based `Fotos/` library and recreates albums under `Albums/`.
- Keeps detected Apple Live Photo pairs together.
- Places files without a usable capture date in `Files Without Metadata/` for review.
- Can embed date and GPS metadata into copied media with ExifTool.
- Supports localized Google Photos folder names and Takeout year folders.

## Quick start

Requires Python 3.10 or newer. ExifTool is optional; install it to read embedded timestamps and embed metadata.

Preview a ZIP export first:

```bash
python3 organize_google_photos_takeout.py \
  -i "/path/to/takeout.zip" \
  -o "/path/to/organized-photos" \
  --dry-run
```

Then run without `--dry-run` to copy the files. Windows users can use `py` in place of `python3`. See [Quick Start](docs/quick-start.md) for installation and platform-specific commands.

## Output

```text
organized-photos/
├── Fotos/YYYY/                  # Chronological library
├── Albums/<album name>/         # Recreated albums
├── Files Without Metadata/      # No usable Takeout or embedded date
└── metadata-report.txt          # Created after a real run
```

## Documentation

- [Quick Start](docs/quick-start.md): requirements, installation, and commands for macOS, Linux, and Windows.
- [Options and workflows](docs/options-and-workflows.md): command-line options, multiple inputs, ZIP extraction, and Live Photos.
- [Metadata and localization](docs/metadata-and-localization.md): date and GPS handling, report details, and recognized folder names.
- [Troubleshooting](docs/troubleshooting.md): common input, extraction, and media metadata issues.

## Photos Viewer

The local browser-based photo viewer has been split into a separate `Photos Viewer` project. This repository now contains only the Google Photos Takeout organizer script and its documentation.
