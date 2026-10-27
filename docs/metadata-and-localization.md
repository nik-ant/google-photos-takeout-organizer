# Metadata and Localization

## Capture dates and GPS

The organizer chooses a timestamp in this order:

1. Google Takeout JSON sidecar `photoTakenTime`.
2. Embedded media timestamps read with ExifTool, when available.
3. Filesystem modification time as a final fallback.

Files whose only date is the filesystem modification time go into `Files Without Metadata/` for manual review. Other dated files go into `Fotos/YYYY/` and, when applicable, their album folder. Output filenames start with the chosen timestamp to make chronological sorting straightforward.

When ExifTool is available, the script writes available date and GPS metadata to copied media and sets copied file modification times to the chosen timestamp. Without ExifTool, it can still use Takeout JSON dates and set modification times, but it cannot read embedded dates or write embedded metadata. Use `--no-embed-metadata` to skip metadata writing. Use `--copy-sidecars` to copy JSON sidecars alongside media; sidecars are not copied by default.

## Metadata report

Each real run creates `metadata-report.txt` in the output folder. It summarizes the scanned media count, files without Takeout JSON timestamps, timestamp fallback usage, source and output paths, and final dates. Consult it when reviewing files in `Files Without Metadata/`.

## File extensions

The script checks for common mismatches between image data and filename extension. For example, JPEG data stored with a `.HEIC` extension can be copied with a corrected extension; the original file is unchanged.

## Recognized Takeout folders

Google Photos exports may use localized library folder names. The script recognizes common forms including:

- `Google Photos`, `Google Fotos`, `Zdjęcia Google`
- `Google Фото`, `Google フォト`, `Google 포토`, `Google 相册`
- Year folders such as `Photos from 2022`, `Fotos von 2022`, `Fotos de 2022`, `Photos de 2022`, `Zdjęcia z 2022`, `Фотографии за 2022`, `2022年の写真`, and `2022년 사진`

Other named folders such as `Belgium (Bruges)`, `Paris 2022 Trip`, and `Dubai (UAE)` are treated as albums.
