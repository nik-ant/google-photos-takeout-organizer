# Options and Workflows

## Inputs and ZIP archives

`--input` (`-i`) accepts one or more existing Google Photos Takeout folders or `.zip` archives. `--output` (`-o`) names the destination folder, which is created when needed.

For a large ZIP export, set a temporary extraction directory explicitly:

```bash
python3 organize_google_photos_takeout.py \
  -i "/path/to/takeout.zip" \
  -o "/path/to/organized-output" \
  --work-dir "/path/to/temporary-work"
```

On Windows PowerShell, a temporary directory can be set with `--work-dir "$env:TEMP\google-takeout-work"`. Without this option, temporary extraction uses a temporary folder beside the output.

## Command-line options

- `--dry-run`: print planned operations without copying media.
- `--work-dir PATH`: choose where ZIP archives are extracted temporarily.
- `--copy-sidecars`: copy matched Takeout JSON sidecars next to the output media.
- `--no-albums`: skip album copies; keep the chronological library and the review folder for files without capture dates.
- `--no-embed-metadata`: do not call ExifTool to write metadata, even when installed.
- `--no-embedded-fallback`: skip embedded timestamp reading. Intended for quick layout previews; it can put older media into the review folder, so omit it for final runs.
- `--verbose`: print each planned or copied file path.

Run `python3 organize_google_photos_takeout.py --help` (or `py` on Windows) for the current command help.

## Live Photos

The organizer detects likely Apple Live Photo pairs by matching a photo and video with the same base name and a close timestamp. The video is copied alongside the photo and receives a `__live` filename suffix. When an album is recreated, the pair is copied there as well.

For example, `IMG_1234.HEIC` and `IMG_1234.MOV` may become:

```text
Fotos/2024/2024-05-01_13-25-10__IMG_1234.HEIC
Fotos/2024/2024-05-01_13-25-10__IMG_1234__live.MOV
```
