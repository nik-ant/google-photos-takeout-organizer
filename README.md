# Google Photos Takeout Organizer

A Python script for organizing a Google Photos Takeout export into a clean local photo library.

The script reads Google Takeout media files and their JSON sidecar metadata, then creates a chronological folder structure while preserving albums. It is designed for exports that contain photos, videos, Live Photos, localized Google Photos folder names, and Google-generated year folders such as `Photos from 2022` or `Fotos von 2022`.

Original Takeout files are never modified. The script copies files into a new output folder.

## What The Script Does

- Organizes the main photo library into `Fotos/YYYY/`.
- Recreates Google Photos albums under `Albums/<album name>/`.
- Sorts files chronologically by prefixing output filenames with the capture timestamp.
- Keeps Live Photo videos next to the matching photo.
- Reads Google Takeout JSON sidecars for date and GPS metadata.
- Uses embedded media metadata as a fallback, especially for videos.
- Places files with no usable timestamp metadata into `Files Without Metadata/`.
- Corrects obvious wrong file extensions, for example JPEG data saved as `.HEIC`.
- Embeds date and GPS metadata into copied files when `exiftool` is installed.
- Creates a `metadata-report.txt` file after each real run.
- Shows progress while extracting, scanning, and organizing.

## Output Structure

Example:

```text
Organized Photos/
  Fotos/
    2024/
      2024-05-01_13-25-10__IMG_1234.HEIC
      2024-05-01_13-25-10__IMG_1234__live.MOV
  Albums/
    Belgium (Bruges)/
      2024-05-01_13-25-10__IMG_1234.HEIC
      2024-05-01_13-25-10__IMG_1234__live.MOV
  Files Without Metadata/
    2026-05-19_11-57-07__UNKNOWN_VIDEO.MP4
  metadata-report.txt
```

`Fotos/` contains the general chronological library.

`Albums/` contains recreated Google Photos albums.

`Files Without Metadata/` contains only files where the script could not find a usable timestamp in Takeout JSON or embedded media metadata.

## Metadata Behavior

The script chooses dates in this order:

1. Google Takeout JSON `photoTakenTime`
2. Embedded media metadata via `exiftool`
3. Filesystem modification time as a last fallback

Files using the last fallback are not placed into normal year folders. They are placed into `Files Without Metadata/` for manual review.

If `exiftool` is installed, the script also writes date and GPS metadata into the copied media files. If `exiftool` is not installed, the script can still organize files using Takeout JSON metadata, but it cannot embed that metadata into the media files.

JSON sidecars are not copied by default. Use `--copy-sidecars` if you want JSON files beside the organized media.

## Localization Support

The script recognizes common localized Google Photos folder names, including:

- `Google Photos`
- `Google Fotos`
- `Zdjęcia Google`
- `Google Фото`
- `Google フォト`
- `Google 포토`
- `Google 相册`

It also recognizes localized year-library folders, for example:

- `Photos from 2022`
- `Fotos von 2022`
- `Fotos de 2022`
- `Photos de 2022`
- `Zdjęcia z 2022`
- `Фотографии за 2022`
- `2022年の写真`
- `2022년 사진`

Folders such as `Belgium (Bruges)`, `Paris 2022 Trip`, or `Dubai (UAE)` are treated as albums.

## Requirements

- Python 3.10 or newer
- Optional but recommended: `exiftool`

Install requirements:

| System | Python | ExifTool |
| --- | --- | --- |
| macOS | `brew install python` | `brew install exiftool` |
| Linux, Debian/Ubuntu | `sudo apt install python3` | `sudo apt install libimage-exiftool-perl` |
| Linux, Fedora | `sudo dnf install python3` | `sudo dnf install perl-Image-ExifTool` |
| Windows, winget | `winget install Python.Python.3` | `winget install OliverBetz.ExifTool` |
| Windows, Chocolatey | `choco install python` | `choco install exiftool` |

After installation, verify:

| System | Command |
| --- | --- |
| macOS/Linux | `python3 --version` |
| Windows | `py --version` |
| All systems | `exiftool -ver` |

## Basic Usage

Download or clone this repository, then open a terminal in the project folder.

| System | Example project folder command |
| --- | --- |
| macOS/Linux | `cd ~/Projects/google-photos-takeout-organizer` |
| Windows PowerShell | `cd "$HOME\Projects\google-photos-takeout-organizer"` |

Run a dry run first. A dry run prints what would happen without copying files:

| System | Dry run command |
| --- | --- |
| macOS/Linux | `python3 organize_google_photos_takeout.py -i "/path/to/takeout.zip" -o "/path/to/organized-output" --dry-run` |
| Windows PowerShell | `py organize_google_photos_takeout.py -i "C:\Path\To\takeout.zip" -o "C:\Path\To\organized-output" --dry-run` |

Run the real copy:

| System | Real run command |
| --- | --- |
| macOS/Linux | `python3 organize_google_photos_takeout.py -i "/path/to/takeout.zip" -o "/path/to/organized-output"` |
| Windows PowerShell | `py organize_google_photos_takeout.py -i "C:\Path\To\takeout.zip" -o "C:\Path\To\organized-output"` |

You can also pass an already extracted Google Photos folder:

| System | Extracted folder command |
| --- | --- |
| macOS/Linux | `python3 organize_google_photos_takeout.py -i "/path/to/Takeout/Google Photos" -o "/path/to/organized-output"` |
| Windows PowerShell | `py organize_google_photos_takeout.py -i "C:\Path\To\Takeout\Google Photos" -o "C:\Path\To\organized-output"` |

## Recommended Command For Large Zip Exports

For large zip files, use `--work-dir` so temporary extraction happens in a known temporary location:

| System | Large zip command |
| --- | --- |
| macOS | `python3 organize_google_photos_takeout.py -i "/path/to/takeout.zip" -o "/path/to/organized-output" --work-dir /tmp/google-takeout-work` |
| Linux | `python3 organize_google_photos_takeout.py -i "/path/to/takeout.zip" -o "/path/to/organized-output" --work-dir /tmp/google-takeout-work` |
| Windows PowerShell | `py organize_google_photos_takeout.py -i "C:\Path\To\takeout.zip" -o "C:\Path\To\organized-output" --work-dir "$env:TEMP\google-takeout-work"` |

Use a new output folder for each important run. This avoids mixing older test output with new results.

## Example Workflows

### macOS

| Step | Command |
| --- | --- |
| Open project | `cd ~/Projects/google-photos-takeout-organizer` |
| Preview | `python3 organize_google_photos_takeout.py -i "$HOME/Downloads/takeout.zip" -o "$HOME/Pictures/Google Photos Organized" --dry-run` |
| Organize | `python3 organize_google_photos_takeout.py -i "$HOME/Downloads/takeout.zip" -o "$HOME/Pictures/Google Photos Organized" --work-dir /tmp/google-takeout-work` |

### Linux

| Step | Command |
| --- | --- |
| Open project | `cd ~/Projects/google-photos-takeout-organizer` |
| Preview | `python3 organize_google_photos_takeout.py -i "$HOME/Downloads/takeout.zip" -o "$HOME/Pictures/google-photos-organized" --dry-run` |
| Organize | `python3 organize_google_photos_takeout.py -i "$HOME/Downloads/takeout.zip" -o "$HOME/Pictures/google-photos-organized" --work-dir /tmp/google-takeout-work` |

### Windows PowerShell

| Step | Command |
| --- | --- |
| Open project | `cd "$HOME\Projects\google-photos-takeout-organizer"` |
| Preview | `py organize_google_photos_takeout.py -i "$HOME\Downloads\takeout.zip" -o "$HOME\Pictures\Google Photos Organized" --dry-run` |
| Organize | `py organize_google_photos_takeout.py -i "$HOME\Downloads\takeout.zip" -o "$HOME\Pictures\Google Photos Organized" --work-dir "$env:TEMP\google-takeout-work"` |

## Useful Options

| Option | Description |
| --- | --- |
| `--dry-run` | Preview the planned output without copying files. |
| `--work-dir /path/to/temp-folder` | Choose where zip archives are extracted temporarily. |
| `--copy-sidecars` | Copy Google Takeout JSON sidecars next to the organized media files. |
| `--no-albums` | Only create the chronological `Fotos/` folder. |
| `--no-embed-metadata` | Do not write metadata into copied media files, even if `exiftool` is installed. |
| `--no-embedded-fallback` | Skip reading embedded media timestamps during scanning. Useful only for fast folder-layout tests. Do not use it for final runs, because older videos may be placed incorrectly without embedded metadata fallback. |
| `--verbose` | Print every planned or copied file path. |

## Live Photos

Google Takeout may export an Apple Live Photo as an image plus a short video. The script detects pairs by matching files with the same base name and a close timestamp.

Example:

```text
IMG_1234.HEIC
IMG_1234.MOV
```

Output:

```text
2024-05-01_13-25-10__IMG_1234.HEIC
2024-05-01_13-25-10__IMG_1234__live.MOV
```

## Metadata Report

After a real run, the script writes:

```text
metadata-report.txt
```

This report includes:

- Total media files scanned
- Files without Takeout JSON timestamps
- Files that used embedded media timestamps
- Files that had no usable timestamp metadata
- Source paths
- Output paths
- Final dates used

Use this report to review files in `Files Without Metadata/`.

## Troubleshooting

### `Input does not exist`

Check that the path exists:

| System | Command |
| --- | --- |
| macOS/Linux | `ls "/path/to/takeout-folder"` |
| Windows PowerShell | `Test-Path "C:\Path\To\takeout.zip"` |

### `PermissionError` while extracting a zip

Use `--work-dir`:

| System | Command |
| --- | --- |
| macOS/Linux | `python3 organize_google_photos_takeout.py -i "/path/to/takeout.zip" -o "/path/to/organized-output" --work-dir /tmp/google-takeout-work` |
| Windows PowerShell | `py organize_google_photos_takeout.py -i "C:\Path\To\takeout.zip" -o "C:\Path\To\organized-output" --work-dir "$env:TEMP\google-takeout-work"` |

### Videos appear in the wrong year

Install `exiftool` and run again without `--no-embedded-fallback`:

| System | Command |
| --- | --- |
| macOS | `brew install exiftool` |
| Debian/Ubuntu | `sudo apt install libimage-exiftool-perl` |
| Fedora | `sudo dnf install perl-Image-ExifTool` |
| Windows, winget | `winget install OliverBetz.ExifTool` |

### Warnings about invalid HEIC files

Some exports contain JPEG files with a `.HEIC` extension. The script detects common mismatches and writes the corrected extension in the output.

## Safety Notes

- The script copies files. It does not delete or modify your original Takeout export.
- Use `--dry-run` before a real run.
- Use a fresh output folder for each full run.
- Keep the original Takeout zip or folder until you have checked the organized output.
