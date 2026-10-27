# Troubleshooting

## `Input does not exist`

Check the input path. On macOS/Linux:

```bash
ls "/path/to/takeout-folder"
```

On Windows PowerShell:

```powershell
Test-Path "C:\Path\To\takeout.zip"
```

Pass an existing Takeout ZIP or Google Photos folder to `-i`.

## `PermissionError` while extracting a ZIP

Choose a temporary directory you can write to with `--work-dir`, for example:

```bash
python3 organize_google_photos_takeout.py -i "/path/to/takeout.zip" -o "/path/to/organized-output" --work-dir "/tmp/google-takeout-work"
```

On Windows PowerShell, use `--work-dir "$env:TEMP\google-takeout-work"`.

## Videos appear in the wrong year or files lack capture dates

Install ExifTool so the organizer can read embedded media timestamps, then run again without `--no-embedded-fallback`. Installation commands are in [Quick Start](quick-start.md).

## ExifTool is unavailable

The script still organizes files using Takeout JSON timestamps. It cannot read embedded dates or embed date/GPS metadata without ExifTool. If JSON sidecars are present, `--copy-sidecars` copies them beside output media.

## Warning about an invalid HEIC file

Some exports contain JPEG data with a `.HEIC` extension. The organizer detects common mismatches and corrects the extension on the copied output file. The source remains untouched.
