# Quick Start

## Requirements

- Python 3.10 or newer.
- ExifTool is optional. It enables embedded timestamp reading and writing date/GPS metadata into copied media.

Install Python and, optionally, ExifTool using your platform's package manager:

- macOS: `brew install python exiftool`
- Debian or Ubuntu: `sudo apt install python3 libimage-exiftool-perl`
- Fedora: `sudo dnf install python3 perl-Image-ExifTool`
- Windows with winget: `winget install Python.Python.3` and optionally `winget install OliverBetz.ExifTool`
- Windows with Chocolatey: `choco install python` and optionally `choco install exiftool`

Check installation with `python3 --version` on macOS/Linux or `py --version` on Windows. Check ExifTool with `exiftool -ver`.

## Preview an export

Run commands from the folder containing `organize_google_photos_takeout.py`. For a ZIP archive on macOS/Linux:

```bash
python3 organize_google_photos_takeout.py -i "/path/to/takeout.zip" -o "/path/to/organized-output" --dry-run
```

On Windows PowerShell:

```powershell
py organize_google_photos_takeout.py -i "C:\Path\To\takeout.zip" -o "C:\Path\To\organized-output" --dry-run
```

The input can also be an extracted Google Photos folder. For example:

```bash
python3 organize_google_photos_takeout.py -i "/path/to/Takeout/Google Photos" -o "/path/to/organized-output" --dry-run
```

## Organize the files

Remove `--dry-run` to copy files to the destination. On macOS/Linux:

```bash
python3 organize_google_photos_takeout.py -i "/path/to/takeout.zip" -o "/path/to/organized-output"
```

On Windows PowerShell:

```powershell
py organize_google_photos_takeout.py -i "C:\Path\To\takeout.zip" -o "C:\Path\To\organized-output"
```

Use a fresh output folder for each full run. For large archives or extraction permission issues, set `--work-dir`; see [Options and workflows](options-and-workflows.md).

The script copies media and does not delete or modify the original Takeout files. Keep the original export until you have reviewed the output.
