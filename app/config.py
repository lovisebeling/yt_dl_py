# app/config.py
"""Réglages persistants de Sonore."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from threading import RLock
from typing import Any

DEFAULT_SETTINGS: dict[str, Any] = {
    "output_dir": str(Path.home() / "Downloads"),
    "ignore_playlists": True,
    "download_from_video": False,
    "removals": [],
    "replacements": [],
}


def application_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(sys.argv[0]).resolve().parent


class SettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path(os.environ.get("SONORE_SETTINGS_PATH", application_dir() / "settings.json"))
        self._lock = RLock()

    def load(self) -> dict[str, Any]:
        with self._lock:
            data = DEFAULT_SETTINGS.copy()
            try:
                saved = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(saved, dict):
                    data.update(saved)
            except (OSError, json.JSONDecodeError):
                pass
            data["removals"] = _string_list(data.get("removals"))
            data["replacements"] = _replacement_list(data.get("replacements"))
            data["output_dir"] = str(data.get("output_dir") or DEFAULT_SETTINGS["output_dir"])
            data["ignore_playlists"] = bool(data.get("ignore_playlists", True))
            data["download_from_video"] = not data["ignore_playlists"]
            return data

    def save(self, settings: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            current = DEFAULT_SETTINGS | settings
            current["removals"] = _string_list(current.get("removals"))
            current["replacements"] = _replacement_list(current.get("replacements"))
            current["ignore_playlists"] = bool(current.get("ignore_playlists", True))
            current["download_from_video"] = not current["ignore_playlists"]
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self.path.with_suffix(".json.tmp")
            temp_path.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temp_path.replace(self.path)
            return current


def _string_list(value: Any) -> list[str]:
    return [item.strip() for item in value if isinstance(item, str) and item.strip()] if isinstance(value, list) else []


def _replacement_list(value: Any) -> list[dict[str, Any]]:
    result = []
    if isinstance(value, list):
        for entry in value:
            if isinstance(entry, dict) and isinstance(entry.get("find"), str) and entry["find"].strip():
                result.append({"find": entry["find"], "replace": str(entry.get("replace", "")), "append": bool(entry.get("append", False))})
    return result
