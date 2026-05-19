#!/usr/bin/env python3
"""
Organize a Google Photos Takeout export chronologically while preserving albums.

The script copies original media bytes into:
  output/Fotos/YYYY/
  output/Albums/<album name>/

Filenames are prefixed with the taken timestamp so Finder/Explorer sorting is
chronological. Google Takeout JSON sidecars are copied next to each output file.
When exiftool is installed, metadata from the sidecar is also written into the
copied media file. Originals are never modified.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


MEDIA_EXTENSIONS = {
    ".3g2",
    ".3gp",
    ".ari",
    ".arw",
    ".avi",
    ".cr2",
    ".cr3",
    ".dng",
    ".gif",
    ".heic",
    ".heif",
    ".jpeg",
    ".jpg",
    ".m4v",
    ".mov",
    ".mp4",
    ".mts",
    ".nef",
    ".orf",
    ".png",
    ".raf",
    ".rw2",
    ".tif",
    ".tiff",
    ".webp",
}

PHOTO_EXTENSIONS = {
    ".arw",
    ".cr2",
    ".cr3",
    ".dng",
    ".gif",
    ".heic",
    ".heif",
    ".jpeg",
    ".jpg",
    ".nef",
    ".orf",
    ".png",
    ".raf",
    ".rw2",
    ".tif",
    ".tiff",
    ".webp",
}

VIDEO_EXTENSIONS = {
    ".3g2",
    ".3gp",
    ".avi",
    ".m4v",
    ".mov",
    ".mp4",
    ".mts",
}

YEAR_RE = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
YEAR_ONLY_RE = re.compile(r"^(?:19|20)\d{2}$")
GOOGLE_PHOTOS_DIR_NAMES = {
    "fotky google",
    "fotos google",
    "google foto",
    "google fotoğraflar",
    "google fotos",
    "google foto's",
    "google photos",
    "google zdjęcia",
    "google фото",
    "google фотки",
    "google フォト",
    "google 포토",
    "google 相册",
    "google 相簿",
    "zdjęcia google",
    "صور google",
}
YEAR_LIBRARY_WORDS = {
    "bilder",
    "bild",
    "foto",
    "foto's",
    "fotos",
    "fotografie",
    "fotografías",
    "fotografias",
    "fotografier",
    "fotografii",
    "fotografije",
    "fotky",
    "fotók",
    "fényképek",
    "afbeeldingen",
    "imágenes",
    "imagenes",
    "imagens",
    "immagini",
    "photos",
    "photo",
    "pictures",
    "pics",
    "zdjęcia",
    "obrázky",
    "obrázkov",
    "snímky",
    "снимки",
    "фотографии",
    "фото",
    "写真",
    "照片",
    "相片",
    "相册",
    "사진",
    "फ़ोटो",
    "صور",
    "תמונות",
    "ภาพถ่าย",
    "ảnh",
}
NON_ALBUM_SYSTEM_FOLDERS = {"archive", "archiv", "trash", "papierkorb", "locked folder"}
SAFE_NAME_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class Progress:
    def __init__(self, label: str, total: int, enabled: bool = True) -> None:
        self.label = label
        self.total = max(total, 0)
        self.enabled = enabled
        self.current = 0
        self.started_at = time.monotonic()
        self.last_draw = 0.0

    def advance(self, step: int = 1) -> None:
        self.current += step
        self.draw()

    def draw(self, force: bool = False) -> None:
        if not self.enabled:
            return
        now = time.monotonic()
        if not force and now - self.last_draw < 0.1 and self.current < self.total:
            return
        self.last_draw = now

        width = 28
        if self.total:
            ratio = min(self.current / self.total, 1)
            filled = int(width * ratio)
            percent = ratio * 100
            count = f"{self.current}/{self.total}"
        else:
            filled = 0
            percent = 0
            count = str(self.current)

        bar = "#" * filled + "-" * (width - filled)
        elapsed = max(now - self.started_at, 0.001)
        rate = self.current / elapsed
        line = f"\r{self.label}: [{bar}] {percent:6.2f}% {count} ({rate:,.1f}/s)"
        print(line, end="", flush=True)

    def finish(self) -> None:
        if not self.enabled:
            return
        self.current = max(self.current, self.total)
        if self.current < self.total:
            self.draw(force=True)
        print()


class CountProgress:
    def __init__(self, label: str, enabled: bool = True) -> None:
        self.label = label
        self.enabled = enabled
        self.started_at = time.monotonic()
        self.last_draw = 0.0
        self.current = 0

    def update(self, current: int, force: bool = False) -> None:
        self.current = current
        if not self.enabled:
            return
        now = time.monotonic()
        if not force and now - self.last_draw < 0.25:
            return
        self.last_draw = now
        elapsed = max(now - self.started_at, 0.001)
        rate = self.current / elapsed
        print(f"\r{self.label}: {self.current:,} ({rate:,.1f}/s)", end="", flush=True)

    def finish(self) -> None:
        if not self.enabled:
            return
        self.update(self.current, force=True)
        print()


@dataclass(frozen=True)
class Metadata:
    timestamp: int | None
    timestamp_source: str
    title: str | None
    latitude: float | None
    longitude: float | None
    altitude: float | None
    raw: dict[str, Any] | None
    sidecar: Path | None


@dataclass(frozen=True)
class MediaItem:
    path: Path
    metadata: Metadata
    album: str | None

    @property
    def taken_at(self) -> datetime:
        if self.metadata.timestamp is not None:
            return datetime.fromtimestamp(self.metadata.timestamp, tz=timezone.utc)
        stat = self.path.stat()
        return datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)

    @property
    def timestamp_source(self) -> str:
        if self.metadata.timestamp is not None:
            return self.metadata.timestamp_source
        return "filesystem-mtime"

    @property
    def is_photo(self) -> bool:
        return self.path.suffix.lower() in PHOTO_EXTENSIONS

    @property
    def is_video(self) -> bool:
        return self.path.suffix.lower() in VIDEO_EXTENSIONS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Organize Google Photos Takeout media chronologically and by album."
    )
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        nargs="+",
        type=Path,
        help="One or more Takeout/Google Photos folders or .zip archives to scan.",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        type=Path,
        help="Destination folder. It will be created if needed.",
    )
    parser.add_argument(
        "--no-albums",
        action="store_true",
        help="Only create the Chronological folder.",
    )
    parser.add_argument(
        "--no-embed-metadata",
        action="store_true",
        help="Do not call exiftool even when it is installed.",
    )
    parser.add_argument(
        "--no-embedded-fallback",
        action="store_true",
        help="Do not read embedded media timestamps during scanning. Useful for fast dry-run folder layout tests.",
    )
    parser.add_argument(
        "--copy-sidecars",
        action="store_true",
        help="Copy Takeout JSON sidecars next to output media files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned operations without writing files.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print every copied file.",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        help="Temporary extraction folder for .zip inputs. Defaults to a temp folder beside the output.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def json_title(data: dict[str, Any] | None) -> str | None:
    if data is None:
        return None
    title = data.get("title")
    return title if isinstance(title, str) and title else None


def sidecar_candidates(media_path: Path, json_by_dir: dict[Path, list[Path]]) -> Iterable[Path]:
    direct_names = (
        media_path.with_name(media_path.name + ".json"),
        media_path.with_name(media_path.name + ".supplemental-metadata.json"),
        media_path.with_suffix(media_path.suffix + ".json"),
        media_path.with_suffix(".json"),
    )
    yielded: set[Path] = set()
    for candidate in direct_names:
        if candidate.exists() and candidate not in yielded:
            yielded.add(candidate)
            yield candidate

    for candidate in json_by_dir.get(media_path.parent, []):
        if candidate not in yielded:
            yielded.add(candidate)
            yield candidate


def find_sidecar(
    media_path: Path,
    json_by_dir: dict[Path, list[Path]],
    json_cache: dict[Path, dict[str, Any] | None],
) -> tuple[Path | None, dict[str, Any] | None]:
    for candidate in sidecar_candidates(media_path, json_by_dir):
        data = json_cache.setdefault(candidate, load_json(candidate))
        if data is None:
            continue
        title = json_title(data)
        if candidate.name.startswith(media_path.name) or title == media_path.name:
            return candidate, data
    return None, None


def parse_timestamp(data: dict[str, Any] | None) -> int | None:
    if not data:
        return None

    for key in ("photoTakenTime", "creationTime"):
        value = data.get(key)
        if isinstance(value, dict):
            timestamp = value.get("timestamp")
            if isinstance(timestamp, str) and timestamp.isdigit():
                return int(timestamp)
            if isinstance(timestamp, int):
                return timestamp
    return None


def number_from_geo(value: Any) -> float | None:
    if isinstance(value, (int, float)) and value not in (0, 0.0):
        return float(value)
    return None


def parse_geo(data: dict[str, Any] | None) -> tuple[float | None, float | None, float | None]:
    if not data:
        return None, None, None

    for key in ("geoDataExif", "geoData"):
        value = data.get(key)
        if not isinstance(value, dict):
            continue
        latitude = number_from_geo(value.get("latitude"))
        longitude = number_from_geo(value.get("longitude"))
        altitude = number_from_geo(value.get("altitude"))
        if latitude is not None and longitude is not None:
            return latitude, longitude, altitude
    return None, None, None


def parse_exif_datetime(value: Any) -> int | None:
    if not isinstance(value, str):
        return None

    value = value.strip()
    if not value or value.startswith("0000:00:00"):
        return None

    match = re.match(
        r"^(\d{4}):(\d{2}):(\d{2})[ T](\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:([+-]\d{2}):?(\d{2})|Z)?$",
        value,
    )
    if not match:
        return None

    year, month, day, hour, minute, second, offset_hour, offset_minute = match.groups()
    try:
        parsed = datetime(
            int(year),
            int(month),
            int(day),
            int(hour),
            int(minute),
            int(second),
            tzinfo=timezone.utc,
        )
    except ValueError:
        return None

    if offset_hour and offset_minute:
        sign = 1 if offset_hour.startswith("+") else -1
        offset_seconds = sign * (abs(int(offset_hour)) * 3600 + int(offset_minute) * 60)
        parsed = datetime.fromtimestamp(parsed.timestamp() - offset_seconds, tz=timezone.utc)

    return int(parsed.timestamp())


def embedded_metadata(path: Path) -> tuple[int | None, float | None, float | None, float | None]:
    if not exiftool_available():
        return None, None, None, None

    command = [
        "exiftool",
        "-json",
        "-n",
        "-api",
        "QuickTimeUTC=1",
        "-DateTimeOriginal",
        "-CreateDate",
        "-MediaCreateDate",
        "-TrackCreateDate",
        "-GPSLatitude",
        "-GPSLongitude",
        "-GPSAltitude",
        str(path),
    ]
    try:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        parsed = json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return None, None, None, None

    if not isinstance(parsed, list) or not parsed or not isinstance(parsed[0], dict):
        return None, None, None, None

    data = parsed[0]
    timestamp = None
    for key in ("DateTimeOriginal", "MediaCreateDate", "CreateDate", "TrackCreateDate"):
        timestamp = parse_exif_datetime(data.get(key))
        if timestamp is not None:
            break

    latitude = number_from_geo(data.get("GPSLatitude"))
    longitude = number_from_geo(data.get("GPSLongitude"))
    altitude = data.get("GPSAltitude")
    altitude = float(altitude) if isinstance(altitude, (int, float)) else None
    return timestamp, latitude, longitude, altitude


def build_json_index(input_roots: list[Path], show_progress: bool) -> dict[Path, list[Path]]:
    json_by_dir: dict[Path, list[Path]] = {}
    progress = CountProgress("Indexing JSON sidecars", enabled=show_progress)
    count = 0
    for root in input_roots:
        for path in root.rglob("*.json"):
            json_by_dir.setdefault(path.parent, []).append(path)
            count += 1
            progress.update(count)
    progress.finish()
    return json_by_dir


def sanitize_name(name: str) -> str:
    cleaned = SAFE_NAME_RE.sub("_", name).strip().strip(".")
    return cleaned or "Untitled Album"


def normalized_folder_name(name: str) -> str:
    return " ".join(name.casefold().replace("_", " ").replace("-", " ").split())


def is_year_library_folder(name: str) -> bool:
    normalized = normalized_folder_name(name)
    if YEAR_ONLY_RE.fullmatch(normalized):
        return True
    if not YEAR_RE.search(normalized):
        return False
    return any(word in normalized for word in YEAR_LIBRARY_WORDS)


def album_for(path: Path, input_roots: list[Path]) -> str | None:
    for root in input_roots:
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue

        if len(relative.parts) < 2:
            return None

        folder = relative.parts[0]
        if is_year_library_folder(folder):
            return None
        if normalized_folder_name(folder) in NON_ALBUM_SYSTEM_FOLDERS:
            return None
        return sanitize_name(folder)
    return None


def scan_media(input_roots: list[Path], show_progress: bool, use_embedded_fallback: bool) -> list[MediaItem]:
    json_by_dir = build_json_index(input_roots, show_progress)
    json_cache: dict[Path, dict[str, Any] | None] = {}
    items: list[MediaItem] = []
    progress = CountProgress("Scanning media files", enabled=show_progress)

    for root in input_roots:
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in MEDIA_EXTENSIONS:
                continue
            sidecar, data = find_sidecar(path, json_by_dir, json_cache)
            timestamp = parse_timestamp(data)
            timestamp_source = "takeout-json" if timestamp is not None else "missing"
            latitude, longitude, altitude = parse_geo(data)
            if use_embedded_fallback and (timestamp is None or latitude is None or longitude is None):
                embedded_timestamp, embedded_latitude, embedded_longitude, embedded_altitude = embedded_metadata(path)
                if timestamp is None:
                    timestamp = embedded_timestamp
                    if timestamp is not None:
                        timestamp_source = "embedded-media"
                if latitude is None:
                    latitude = embedded_latitude
                if longitude is None:
                    longitude = embedded_longitude
                if altitude is None:
                    altitude = embedded_altitude
            metadata = Metadata(
                timestamp=timestamp,
                timestamp_source=timestamp_source,
                title=json_title(data),
                latitude=latitude,
                longitude=longitude,
                altitude=altitude,
                raw=data,
                sidecar=sidecar,
            )
            items.append(MediaItem(path=path, metadata=metadata, album=album_for(path, input_roots)))
            progress.update(len(items))

    items.sort(key=lambda item: (item.taken_at, item.path.name.lower(), str(item.path)))
    progress.finish()
    return items


def prepare_inputs(
    inputs: list[Path],
    output: Path,
    work_dir: Path | None,
    show_progress: bool,
) -> tuple[list[Path], tempfile.TemporaryDirectory[str] | None]:
    folders: list[Path] = []
    zip_inputs: list[Path] = []

    for path in inputs:
        if path.is_dir():
            folders.extend(google_photos_roots(path))
        elif path.is_file() and path.suffix.lower() == ".zip":
            zip_inputs.append(path)
        else:
            print(f"Unsupported input. Use a folder or .zip archive: {path}", file=sys.stderr)
            raise SystemExit(2)

    temp_context: tempfile.TemporaryDirectory[str] | None = None
    if zip_inputs:
        if work_dir is None:
            output.parent.mkdir(parents=True, exist_ok=True)
            temp_context = tempfile.TemporaryDirectory(prefix=".takeout-extract-", dir=output.parent)
            extract_root = Path(temp_context.name)
        else:
            extract_root = work_dir.expanduser().resolve()
            extract_root.mkdir(parents=True, exist_ok=True)

        for archive in zip_inputs:
            archive_dir = extract_root / archive.stem
            archive_dir.mkdir(parents=True, exist_ok=True)
            print(f"Extracting {archive} to {archive_dir}")
            with zipfile.ZipFile(archive) as zip_file:
                members = zip_file.infolist()
                progress = Progress("Extracting", len(members), enabled=show_progress)
                for member in members:
                    zip_file.extract(member, archive_dir)
                    progress.advance()
                progress.finish()
            folders.extend(google_photos_roots(archive_dir))

    return folders, temp_context


def google_photos_roots(path: Path) -> list[Path]:
    if normalized_folder_name(path.name) in GOOGLE_PHOTOS_DIR_NAMES:
        return [path]

    found: list[Path] = []
    pending: list[tuple[Path, int]] = [(path, 0)]
    while pending:
        current, depth = pending.pop(0)
        if depth >= 4:
            continue
        try:
            children = list(current.iterdir())
        except OSError:
            continue
        for child in children:
            if not child.is_dir():
                continue
            if normalized_folder_name(child.name) in GOOGLE_PHOTOS_DIR_NAMES:
                found.append(child)
            else:
                pending.append((child, depth + 1))
    return found[:1] if found else [path]


def live_photo_pairs(items: list[MediaItem]) -> dict[Path, MediaItem]:
    by_stem: dict[str, list[MediaItem]] = {}
    for item in items:
        by_stem.setdefault(item.path.stem.lower(), []).append(item)

    pairs: dict[Path, MediaItem] = {}
    for group in by_stem.values():
        photos = [item for item in group if item.is_photo]
        videos = [item for item in group if item.is_video and item.path.suffix.lower() in {".mov", ".mp4"}]
        for photo in photos:
            best: MediaItem | None = None
            best_delta: float | None = None
            for video in videos:
                delta = abs((photo.taken_at - video.taken_at).total_seconds())
                if best_delta is None or delta < best_delta:
                    best = video
                    best_delta = delta
            if best is not None and (best_delta is None or best_delta <= 3):
                pairs[photo.path] = best
    return pairs


def timestamp_prefix(item: MediaItem) -> str:
    return item.taken_at.astimezone(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")


def detected_image_suffix(path: Path) -> str | None:
    try:
        with path.open("rb") as handle:
            header = handle.read(64)
    except OSError:
        return None

    if header.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if header.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    if header.startswith((b"II*\x00", b"MM\x00*")):
        return ".tif"
    if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return ".webp"
    if header[4:8] == b"ftyp" and header[8:12] in {
        b"heic",
        b"heix",
        b"hevc",
        b"hevx",
        b"mif1",
        b"msf1",
    }:
        return ".heic"
    return None


def output_filename(item: MediaItem) -> str:
    suffix = item.path.suffix
    if item.is_photo:
        detected_suffix = detected_image_suffix(item.path)
        if detected_suffix is not None and detected_suffix != suffix.lower():
            suffix = detected_suffix

    return f"{timestamp_prefix(item)}__{item.path.stem}{suffix}"


def unique_destination(directory: Path, filename: str, used: set[Path]) -> Path:
    destination = directory / filename
    if destination not in used and not destination.exists():
        used.add(destination)
        return destination

    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 2
    while True:
        candidate = directory / f"{stem}-{counter}{suffix}"
        if candidate not in used and not candidate.exists():
            used.add(candidate)
            return candidate
        counter += 1


def planned_destinations(
    items: list[MediaItem],
    output: Path,
    include_albums: bool,
    pairs: dict[Path, MediaItem],
) -> list[tuple[MediaItem, Path, str]]:
    operations: list[tuple[MediaItem, Path, str]] = []
    used: set[Path] = set()
    paired_video_paths = {video.path for video in pairs.values()}

    for item in items:
        if item.path in paired_video_paths:
            continue

        base_name = output_filename(item)
        if item.timestamp_source == "filesystem-mtime":
            review_dir = output / "Files Without Metadata"
            operations.append((item, unique_destination(review_dir, base_name, used), "without-metadata"))
            continue

        year = item.taken_at.astimezone(timezone.utc).strftime("%Y")
        chronological_dir = output / "Fotos" / year
        operations.append((item, unique_destination(chronological_dir, base_name, used), "chronological"))

        if include_albums and item.album:
            album_dir = output / "Albums" / item.album
            operations.append((item, unique_destination(album_dir, base_name, used), "album"))

        paired_video = pairs.get(item.path)
        if paired_video is None:
            continue

        live_name = f"{timestamp_prefix(item)}__{item.path.stem}__live{paired_video.path.suffix}"
        if paired_video.timestamp_source == "filesystem-mtime":
            review_dir = output / "Files Without Metadata"
            operations.append((paired_video, unique_destination(review_dir, live_name, used), "without-metadata-live-photo"))
            continue

        operations.append((paired_video, unique_destination(chronological_dir, live_name, used), "live-photo"))
        if include_albums and item.album:
            album_dir = output / "Albums" / item.album
            operations.append((paired_video, unique_destination(album_dir, live_name, used), "album-live-photo"))

    return operations


def copy_media(src: Path, dst: Path, dry_run: bool) -> None:
    if dry_run:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def copy_sidecar(item: MediaItem, dst: Path, dry_run: bool, enabled: bool) -> None:
    if not enabled or item.metadata.sidecar is None or dry_run:
        return
    sidecar_dst = dst.with_name(dst.name + ".json")
    shutil.copy2(item.metadata.sidecar, sidecar_dst)


def set_mtime(item: MediaItem, dst: Path, dry_run: bool) -> None:
    if item.metadata.timestamp is None or dry_run:
        return
    os.utime(dst, (item.metadata.timestamp, item.metadata.timestamp))


def exiftool_available() -> bool:
    return shutil.which("exiftool") is not None


def exif_datetime(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y:%m:%d %H:%M:%S")


def decimal_to_dms(value: float) -> str:
    absolute = abs(value)
    degrees = int(absolute)
    minutes_float = (absolute - degrees) * 60
    minutes = int(minutes_float)
    seconds = (minutes_float - minutes) * 60
    return f"{degrees} deg {minutes}' {seconds:.6f}\""


def embed_metadata(item: MediaItem, dst: Path, dry_run: bool) -> bool:
    if dry_run:
        return False

    args = ["exiftool", "-overwrite_original", "-P"]
    if item.metadata.timestamp is not None:
        dt = exif_datetime(item.metadata.timestamp)
        args.extend(
            [
                f"-DateTimeOriginal={dt}",
                f"-CreateDate={dt}",
                f"-ModifyDate={dt}",
                f"-MediaCreateDate={dt}",
                f"-TrackCreateDate={dt}",
            ]
        )

    if item.metadata.latitude is not None and item.metadata.longitude is not None:
        args.extend(
            [
                f"-GPSLatitude={decimal_to_dms(item.metadata.latitude)}",
                f"-GPSLatitudeRef={'N' if item.metadata.latitude >= 0 else 'S'}",
                f"-GPSLongitude={decimal_to_dms(item.metadata.longitude)}",
                f"-GPSLongitudeRef={'E' if item.metadata.longitude >= 0 else 'W'}",
            ]
        )
        if item.metadata.altitude is not None:
            args.extend(
                [
                    f"-GPSAltitude={abs(item.metadata.altitude)}",
                    f"-GPSAltitudeRef={0 if item.metadata.altitude >= 0 else 1}",
                ]
            )

    if len(args) == 3:
        return False

    args.append(str(dst))
    try:
        subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    except subprocess.CalledProcessError as error:
        message = error.stderr.strip() if error.stderr else "unknown exiftool error"
        print(f"Warning: could not embed metadata in {dst}: {message}", file=sys.stderr)
        return False
    return True


def write_metadata_report(
    output: Path,
    items: list[MediaItem],
    operations: list[tuple[MediaItem, Path, str]],
    dry_run: bool,
) -> Path | None:
    if dry_run:
        return None

    report_path = output / "metadata-report.txt"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)

    destinations_by_source: dict[Path, list[Path]] = {}
    for item, destination, _reason in operations:
        destinations_by_source.setdefault(item.path, []).append(destination)

    missing_takeout = [item for item in items if item.metadata.timestamp_source != "takeout-json"]
    embedded = [item for item in missing_takeout if item.metadata.timestamp_source == "embedded-media"]
    filesystem = [item for item in missing_takeout if item.timestamp_source == "filesystem-mtime"]

    with report_path.open("w", encoding="utf-8") as handle:
        handle.write("Google Photos Takeout Organizer Metadata Report\n")
        handle.write(f"Generated: {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")
        handle.write(f"Total media files scanned: {len(items)}\n")
        handle.write(f"Files without Takeout JSON timestamp: {len(missing_takeout)}\n")
        handle.write(f"Used embedded media timestamp: {len(embedded)}\n")
        handle.write(f"Used filesystem modification time: {len(filesystem)}\n\n")
        if filesystem:
            handle.write(f"Files without any usable timestamp metadata folder: {output / 'Files Without Metadata'}\n\n")

        if not missing_takeout:
            handle.write("All media files had usable Takeout JSON timestamps.\n")
            return report_path

        handle.write("Files Without Takeout JSON Timestamp\n")
        handle.write("====================================\n\n")
        for item in sorted(missing_takeout, key=lambda media: (media.taken_at, str(media.path))):
            final_date = item.taken_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            handle.write(f"Source: {item.path}\n")
            handle.write(f"Timestamp source used: {item.timestamp_source}\n")
            handle.write(f"Final date used: {final_date}\n")
            handle.write(f"Sidecar: {item.metadata.sidecar if item.metadata.sidecar else 'not found'}\n")
            handle.write(f"Album: {item.album if item.album else 'none'}\n")
            destinations = destinations_by_source.get(item.path, [])
            if destinations:
                handle.write("Output files:\n")
                for destination in destinations:
                    handle.write(f"  - {destination}\n")
            else:
                handle.write("Output files: none\n")
            handle.write("\n")

    return report_path


def run() -> int:
    args = parse_args()
    requested_inputs = [path.expanduser().resolve() for path in args.input]
    output = args.output.expanduser().resolve()

    missing = [path for path in requested_inputs if not path.exists()]
    if missing:
        for path in missing:
            print(f"Input does not exist: {path}", file=sys.stderr)
        return 2

    input_roots, temp_context = prepare_inputs(requested_inputs, output, args.work_dir, not args.verbose)
    try:
        items = scan_media(input_roots, not args.verbose, not args.no_embedded_fallback)
        pairs = live_photo_pairs(items)
        operations = planned_destinations(items, output, not args.no_albums, pairs)
        can_embed = not args.no_embed_metadata and exiftool_available()

        if not can_embed and not args.no_embed_metadata:
            if args.copy_sidecars:
                print("exiftool was not found; copied JSON sidecars and file mtimes will preserve Takeout metadata.")
            else:
                print(
                    "exiftool was not found; media will be copied and file mtimes set, "
                    "but JSON metadata will not be embedded. Install exiftool for embedded date/GPS metadata."
                )

        copied = 0
        embedded = 0
        progress = Progress("Organizing", len(operations), enabled=not args.verbose and not args.dry_run)
        for item, destination, reason in operations:
            if args.verbose or args.dry_run:
                print(f"{reason}: {item.path} -> {destination}")
            copy_media(item.path, destination, args.dry_run)
            copy_sidecar(item, destination, args.dry_run, args.copy_sidecars)
            set_mtime(item, destination, args.dry_run)
            if can_embed and embed_metadata(item, destination, args.dry_run):
                embedded += 1
            copied += 1
            progress.advance()
        progress.finish()

        report_path = write_metadata_report(output, items, operations, args.dry_run)
        albums = len({item.album for item in items if item.album})
        missing_timestamps = sum(1 for item in items if item.metadata.timestamp_source != "takeout-json")
        filesystem_timestamps = sum(1 for item in items if item.timestamp_source == "filesystem-mtime")
        corrected_extensions = sum(
            1
            for item, destination, _reason in operations
            if item.path.suffix.lower() != destination.suffix.lower()
        )
        print(
            f"{'Planned' if args.dry_run else 'Organized'} {len(items)} media files "
            f"into {copied} output files across {albums} albums. "
            f"Live Photo pairs detected: {len(pairs)}. "
            f"Metadata embedded with exiftool: {embedded} files. "
            f"Missing Takeout timestamps: {missing_timestamps}. "
            f"Files without usable timestamp metadata: {filesystem_timestamps}. "
            f"Corrected file extensions: {corrected_extensions}."
        )
        if report_path is not None:
            print(f"Metadata report: {report_path}")
        return 0
    finally:
        if temp_context is not None:
            temp_context.cleanup()


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except BrokenPipeError:
        raise SystemExit(0)
