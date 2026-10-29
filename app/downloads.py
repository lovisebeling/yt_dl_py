"""Audio downloads via yt-dlp, progress reporting, and ZIP archives."""
from __future__ import annotations

import queue
import re
import shutil
import tempfile
import threading
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from app.config import SettingsStore

_INVALID_WINDOWS_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_filename(name: str) -> str:
    cleaned = _INVALID_WINDOWS_CHARS.sub("_", name).rstrip(" .")
    return re.sub(r"\s+", " ", cleaned).strip()[:180] or "audio"


def clean_title(title: str, settings: dict[str, Any]) -> str:
    for text in settings.get("removals", []):
        if text:
            title = title.replace(text, "")
    for rule in settings.get("replacements", []):
        find, replacement = rule.get("find", ""), rule.get("replace", "")
        if not find:
            continue
        if rule.get("append"):
            title = title.replace(find, "").rstrip()
            if title and replacement and not replacement[0].isspace():
                title += " "
            title += replacement
        else:
            title = title.replace(find, replacement)
    return re.sub(r"\s+", " ", title).strip()


@dataclass
class DownloadJob:
    job_id: str
    url: str
    output_dir: str
    mode: str
    state: str = "queued"
    events: queue.Queue[dict[str, Any]] = field(default_factory=queue.Queue)
    thread: threading.Thread | None = None

    def emit(self, event: str, **data: Any) -> None:
        self.events.put({"event": event, "job_id": self.job_id, **data})


class DownloadManager:
    def __init__(self, settings_store: SettingsStore) -> None:
        self.settings_store = settings_store
        self.jobs: dict[str, DownloadJob] = {}
        self._lock = threading.Lock()

    def start(self, url: str, output_dir: str, mode: str) -> DownloadJob:
        if not url.startswith(("https://", "http://")):
            raise ValueError("Enter a valid YouTube video URL.")
        if mode not in {"single", "from_video"}:
            raise ValueError("The selected download mode is invalid.")
        destination = Path(output_dir).expanduser()
        if not destination.exists() or not destination.is_dir():
            raise ValueError("The output folder does not exist.")
        job = DownloadJob(uuid4().hex, url, str(destination.resolve()), mode)
        with self._lock:
            self.jobs[job.job_id] = job
        job.thread = threading.Thread(target=self._run, args=(job,), name=f"download-{job.job_id[:8]}", daemon=True)
        job.thread.start()
        return job

    def get(self, job_id: str) -> DownloadJob | None:
        with self._lock:
            return self.jobs.get(job_id)

    def _run(self, job: DownloadJob) -> None:
        job.state = "running"
        job.emit("log", message="Analyzing link…")
        settings = self.settings_store.load()
        try:
            with tempfile.TemporaryDirectory(prefix="sonore_") as temp_dir:
                template = str(Path(temp_dir) / "%(playlist_index)05d_%(title)s.%(ext)s")
                entry_progress: dict[int, float] = {}

                def hook(data: dict[str, Any]) -> None:
                    status = data.get("status")
                    if status == "downloading":
                        index = int(data.get("playlist_index") or 1)
                        total = int(data.get("n_entries") or 1)
                        current = data.get("downloaded_bytes") or 0
                        size = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
                        percent = min(100.0, current * 100 / size) if size else 0.0
                        entry_progress[index] = percent
                        aggregate = sum(entry_progress.values()) / max(total, len(entry_progress))
                        job.emit("progress", percent=aggregate, current=index, total=total, status="Downloading")
                    elif status == "finished":
                        job.emit("progress", percent=100.0, current=int(data.get("playlist_index") or 1), total=int(data.get("n_entries") or 1), status="Converting to MP3…")

                options: dict[str, Any] = {
                    "format": "bestaudio/best", "outtmpl": template,
                    "noplaylist": job.mode == "single", "ignoreerrors": False,
                    "progress_hooks": [hook],
                    "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}],
                    "quiet": True, "no_warnings": True,
                }
                if job.mode == "from_video":
                    playlist_index = self._playlist_index(job.url)
                    if playlist_index is not None:
                        options["playliststart"] = playlist_index
                        options["playlistend"] = -1
                ffmpeg_path = self._bundled_ffmpeg()
                if ffmpeg_path:
                    options["ffmpeg_location"] = ffmpeg_path
                with YoutubeDL(options) as ydl:
                    info = ydl.extract_info(job.url, download=True)
                if not info:
                    raise DownloadError("The video or playlist did not provide any audio files.")
                candidates = sorted(Path(temp_dir).glob("*.mp3"))
                if not candidates:
                    raise DownloadError("No MP3 file was created. Check that FFmpeg is installed.")
                results = self._result_files(candidates, info, settings)
                if len(results) == 1:
                    destination = self._unique_path(Path(job.output_dir) / f"{sanitize_filename(results[0][1])}.mp3")
                    shutil.move(str(results[0][0]), str(destination))
                else:
                    title = sanitize_filename(str(info.get("title") or "playlist"))
                    destination = self._unique_path(Path(job.output_dir) / f"{title}.zip")
                    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                        used_names: set[str] = set()
                        for source, name in results:
                            safe = sanitize_filename(name)
                            candidate_name, number = f"{safe}.mp3", 2
                            while candidate_name.lower() in used_names:
                                candidate_name = f"{safe} ({number}).mp3"
                                number += 1
                            used_names.add(candidate_name.lower())
                            archive.write(source, candidate_name)
                job.state = "completed"
                job.emit("progress", percent=100.0, current=len(results), total=len(results), status="Complete")
                job.emit("completed", path=str(destination), count=len(results), archive=destination.suffix.lower() == ".zip")
                job.emit("log", message=f"✓ {len(results)} file(s) ready: {destination}")
        except Exception as error:
            job.state = "failed"
            message = self._readable_error(error)
            job.emit("failed", message=message)
            job.emit("log", message=f"✗ {message}")

    @staticmethod
    def _result_files(candidates: list[Path], info: dict[str, Any], settings: dict[str, Any]) -> list[tuple[Path, str]]:
        entries = info.get("entries") if info.get("_type") == "playlist" else None
        metadata_by_index = {
            int(entry["playlist_index"]): entry
            for entry in entries or []
            if entry and entry.get("playlist_index") is not None
        }
        results = []
        for path in candidates:
            match = re.match(r"^(\d+)_", path.stem)
            index = int(match.group(1)) if match else None
            entry = metadata_by_index.get(index, info)
            fallback_title = path.stem[match.end():] if match else path.stem
            title = clean_title(str(entry.get("title") or fallback_title), settings)
            results.append((path, title or path.stem))
        return results

    @staticmethod
    def _unique_path(path: Path) -> Path:
        if not path.exists():
            return path
        for index in range(1, 10000):
            candidate = path.with_name(f"{path.stem} ({index}){path.suffix}")
            if not candidate.exists():
                return candidate
        raise OSError("Could not find an available filename.")

    @staticmethod
    def _playlist_index(url: str) -> int | None:
        """Find the current video's index before downloading the rest of a playlist."""
        query = parse_qs(urlparse(url).query)
        if not query.get("list"):
            return None
        explicit_index = query.get("index", [""])[0]
        if explicit_index.isdigit() and int(explicit_index) > 0:
            return int(explicit_index)
        video_id = (query.get("v") or [urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]])[0]
        try:
            with YoutubeDL({"extract_flat": "in_playlist", "quiet": True, "no_warnings": True}) as ydl:
                info = ydl.extract_info(url, download=False)
            entries = info.get("entries") or [] if info else []
            for position, entry in enumerate(entries, 1):
                if entry and str(entry.get("id", "")) == video_id:
                    return int(entry.get("playlist_index") or position)
        except Exception as error:
            raise DownloadError("Could not find this video's position in the playlist.") from error
        raise DownloadError("This video was not found in the playlist from the provided link.")

    @staticmethod
    def _bundled_ffmpeg() -> str | None:
        """Find FFmpeg bundled with the PyInstaller app, if present."""
        import sys

        roots = [Path(getattr(sys, "_MEIPASS", "")), Path(sys.executable).resolve().parent]
        for root in roots:
            if str(root) and root != Path("."):
                binary = root / "tools" / "ffmpeg" / "ffmpeg.exe"
                if binary.is_file():
                    return str(binary)
        return None

    @staticmethod
    def _readable_error(error: Exception) -> str:
        message = str(error).strip() or error.__class__.__name__
        lowered = message.lower()
        if "403" in lowered and ("forbidden" in lowered or "http error 403" in lowered):
            return (
                "YouTube rejected the audio stream (HTTP 403). Update yt-dlp and rebuild the app; "
                "if the error persists, try again later and check your VPN/proxy or a temporary IP block. "
                f"Details: {message[:400]}"
            )
        if "ffmpeg" in lowered:
            return f"FFmpeg could not be found. Install it and add it to PATH. Details: {message}"
        return message[:800]
