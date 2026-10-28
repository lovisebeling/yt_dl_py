"""Interface principale CustomTkinter de Sonore."""
from __future__ import annotations

import json
import queue
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import customtkinter as ctk

from app.config import SettingsStore
from app.downloads import clean_title, sanitize_filename
from app.settings_window import SettingsWindow

API_BASE = "http://127.0.0.1:8765"


class SonoreApp(ctk.CTk):
    def __init__(self, settings_store: SettingsStore) -> None:
        super().__init__()
        self.settings_store = settings_store
        self.settings = settings_store.load()
        self.job_id: str | None = None
        self.is_downloading = False
        self.after_id: str | None = None
        self.title("Sonore — YouTube vers MP3")
        self.geometry("820x640")
        self.minsize(700, 570)
        self.configure(fg_color="#101216")
        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(80, self.url_entry.focus_set)

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=34, pady=(26, 10))
        ctk.CTkLabel(header, text="sonore", font=ctk.CTkFont(size=28, weight="bold"), text_color="#f0f2f5").pack(side="left")
        ctk.CTkLabel(header, text="AUDIO DOWNLOADER", font=ctk.CTkFont(size=10, weight="bold"), text_color="#727b89").pack(side="left", padx=(10, 0), pady=(9, 0))
        ctk.CTkButton(header, text="⚙  Réglages", width=120, height=34, fg_color="#20242b", hover_color="#303640", command=self._open_settings).pack(side="right", pady=2)

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew", padx=34, pady=10)
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(1, weight=1)
        card = ctk.CTkFrame(content, corner_radius=18, fg_color="#191c22", border_width=1, border_color="#252a33")
        card.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text="Télécharger votre audio", font=ctk.CTkFont(size=20, weight="bold"), anchor="w").grid(row=0, column=0, columnspan=2, sticky="ew", padx=22, pady=(20, 4))
        ctk.CTkLabel(card, text="Collez un lien YouTube pour enregistrer l’audio en MP3.", text_color="#9098a5", anchor="w").grid(row=1, column=0, columnspan=2, sticky="ew", padx=22, pady=(0, 15))
        self.url_entry = ctk.CTkEntry(card, height=46, corner_radius=10, placeholder_text="https://www.youtube.com/watch?v=…", font=ctk.CTkFont(size=13))
        self.url_entry.grid(row=2, column=0, sticky="ew", padx=(22, 10), pady=(0, 12))
        self.url_entry.bind("<Return>", self._submit)
        self.download_button = ctk.CTkButton(card, text="Télécharger  ↓", width=148, height=46, corner_radius=10, font=ctk.CTkFont(size=13, weight="bold"), command=self._submit)
        self.download_button.grid(row=2, column=1, sticky="e", padx=(0, 22), pady=(0, 12))
        self.folder_var = tk.StringVar(value=self.settings["output_dir"])
        ctk.CTkLabel(card, text="Enregistrer dans", font=ctk.CTkFont(size=11, weight="bold"), text_color="#aeb4bf", anchor="w").grid(row=3, column=0, columnspan=2, sticky="ew", padx=22)
        folder_row = ctk.CTkFrame(card, fg_color="transparent")
        folder_row.grid(row=4, column=0, columnspan=2, sticky="ew", padx=22, pady=(5, 14))
        folder_row.grid_columnconfigure(0, weight=1)
        self.folder_entry = ctk.CTkEntry(folder_row, textvariable=self.folder_var, height=36, state="readonly", fg_color="#13161b")
        self.folder_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(folder_row, text="Parcourir", width=96, height=36, fg_color="#30353d", hover_color="#414752", command=self._choose_folder).grid(row=0, column=1)
        self.single_var = tk.BooleanVar(value=bool(self.settings.get("ignore_playlists", True)))
        self.from_video_var = tk.BooleanVar(value=not self.single_var.get())
        ctk.CTkRadioButton(card, text="Ignorer les playlists", variable=self.single_var, value=True, command=self._single_selected, font=ctk.CTkFont(size=12)).grid(row=5, column=0, sticky="w", padx=22, pady=(0, 7))
        ctk.CTkRadioButton(card, text="Télécharger cette vidéo et celles après elle dans la playlist", variable=self.single_var, value=False, command=self._playlist_selected, font=ctk.CTkFont(size=12)).grid(row=6, column=0, columnspan=2, sticky="w", padx=22, pady=(0, 20))

        console_card = ctk.CTkFrame(content, corner_radius=16, fg_color="#191c22", border_width=1, border_color="#252a33")
        console_card.grid(row=1, column=0, sticky="nsew")
        console_card.grid_columnconfigure(0, weight=1)
        console_card.grid_rowconfigure(1, weight=1)
        bar = ctk.CTkFrame(console_card, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=18, pady=(15, 8))
        ctk.CTkLabel(bar, text="CONSOLE", font=ctk.CTkFont(size=10, weight="bold"), text_color="#a8b0bc").pack(side="left")
        self.status_label = ctk.CTkLabel(bar, text="PRÊT", font=ctk.CTkFont(size=10, weight="bold"), text_color="#71d6a2")
        self.status_label.pack(side="right")
        self.console = ctk.CTkTextbox(console_card, font=ctk.CTkFont(family="Consolas", size=12), fg_color="#111419", text_color="#c5cbd4", corner_radius=10, wrap="word")
        self.console.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 10))
        self.console.configure(state="disabled")
        self.progress = ctk.CTkProgressBar(console_card, height=5, progress_color="#54d29a", fg_color="#282d35")
        self.progress.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 15))
        self.progress.set(0)
        self._log("Prêt. Collez un lien YouTube pour commencer.")

        footer = ctk.CTkLabel(self, text="Traitement local · sortie audio MP3 192 kb/s", text_color="#626b77", font=ctk.CTkFont(size=10))
        footer.grid(row=2, column=0, pady=(0, 14))

    def _log(self, message: str) -> None:
        self.console.configure(state="normal")
        self.console.insert("end", message + "\n")
        self.console.see("end")
        self.console.configure(state="disabled")

    def _choose_folder(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.folder_var.get() or None, title="Choisir le dossier de destination")
        if selected:
            self.folder_var.set(selected)
            self._save_preferences()

    def _single_selected(self) -> None:
        self.from_video_var.set(False)
        self._save_preferences()

    def _playlist_selected(self) -> None:
        self.single_var.set(False)
        self.from_video_var.set(True)
        self._save_preferences()

    def _save_preferences(self) -> None:
        self.settings.update({"output_dir": self.folder_var.get(), "ignore_playlists": self.single_var.get(), "download_from_video": self.from_video_var.get()})
        try:
            self.settings = self.settings_store.save(self.settings)
        except OSError as error:
            self._log(f"Impossible d’enregistrer les réglages : {error}")

    def _api(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
        request = Request(API_BASE + path, data=data, headers={"Content-Type": "application/json"}, method=method)
        try:
            with urlopen(request, timeout=3) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            detail = json.loads(error.read().decode("utf-8")).get("detail", str(error))
            raise ValueError(str(detail)) from error
        except (URLError, TimeoutError, OSError) as error:
            raise RuntimeError("Le serveur local ne répond pas. Fermez puis relancez l’application.") from error

    def _submit(self, _event: tk.Event | None = None) -> str:
        if self.is_downloading:
            return "break"
        url = self.url_entry.get().strip()
        if not url:
            self._log("Collez d’abord un lien YouTube.")
            self.url_entry.focus_set()
            return "break"
        self._save_preferences()
        mode = "single" if self.single_var.get() else "from_video"
        self.is_downloading = True
        self.download_button.configure(state="disabled", text="En cours…")
        self.status_label.configure(text="CONNEXION…", text_color="#f4bf64")
        self.progress.set(0)
        self._log(f"Demande de téléchargement : {url}")
        threading.Thread(target=self._start_job, args=(url, self.folder_var.get(), mode), daemon=True).start()
        return "break"

    def _start_job(self, url: str, output_dir: str, mode: str) -> None:
        try:
            result = self._api("POST", "/downloads", {"url": url, "output_dir": output_dir, "mode": mode})
            self.after(0, lambda: self._job_started(result["job_id"]))
        except Exception as error:
            self.after(0, lambda message=str(error): self._job_failed(message))

    def _job_started(self, job_id: str) -> None:
        self.job_id = job_id
        self.status_label.configure(text="TÉLÉCHARGEMENT", text_color="#f4bf64")
        self._poll_events()

    def _poll_events(self) -> None:
        job_id = self.job_id
        if not job_id:
            return
        threading.Thread(target=self._fetch_events, args=(job_id,), daemon=True).start()

    def _fetch_events(self, job_id: str) -> None:
        try:
            events = self._api("GET", f"/downloads/{job_id}/events").get("events", [])
            self.after(0, lambda: self._handle_events(job_id, events))
        except Exception as error:
            self.after(0, lambda message=str(error): self._job_failed(message))

    def _handle_events(self, job_id: str, events: list[dict[str, Any]]) -> None:
        if job_id != self.job_id:
            return
        for event in events:
            kind = event.get("event")
            if kind == "log":
                self._log(str(event.get("message", "")))
            elif kind == "progress":
                self.progress.set(max(0.0, min(1.0, float(event.get("percent", 0)) / 100)))
                self.status_label.configure(text=f"{event.get('status', 'EN COURS')} · {event.get('percent', 0):.0f} %", text_color="#f4bf64")
            elif kind == "completed":
                self.progress.set(1)
                self.status_label.configure(text="TERMINÉ", text_color="#71d6a2")
                self._finish_job()
            elif kind == "failed":
                self.status_label.configure(text="ÉCHEC", text_color="#ff8282")
                self._finish_job()
        if self.is_downloading:
            self.after_id = self.after(250, self._poll_events)

    def _finish_job(self) -> None:
        self.is_downloading = False
        self.download_button.configure(state="normal", text="Télécharger  ↓")
        self.job_id = None
        self.url_entry.focus_set()

    def _job_failed(self, message: str) -> None:
        if not self.winfo_exists():
            return
        self._log(f"✗ {message}")
        self.status_label.configure(text="ÉCHEC", text_color="#ff8282")
        self._finish_job()

    def _open_settings(self) -> None:
        def save_rules(changes: dict[str, Any]) -> None:
            self.settings.update(changes)
            try:
                self.settings = self.settings_store.save(self.settings)
                self._log("Réglages des titres enregistrés.")
            except OSError as error:
                self._log(f"Impossible d’enregistrer les réglages : {error}")
        SettingsWindow(self, self.settings, save_rules)

    def _apply_title_rules_to_folder(self, dialog_parent: tk.Misc) -> None:
        folder = filedialog.askdirectory(
            title="Choisir le dossier dont les titres seront mis à jour",
            parent=dialog_parent,
        )
        if not folder:
            return
        supported = {".mp3", ".m4a", ".wav", ".flac", ".aac", ".ogg", ".opus", ".wma"}
        files = [path for path in Path(folder).iterdir() if path.is_file() and path.suffix.lower() in supported]
        changes = [(path, sanitize_filename(clean_title(path.stem, self.settings)) or path.stem) for path in files]
        changes = [(path, name) for path, name in changes if name != path.stem]
        if not changes:
            messagebox.showinfo("Titres", "Aucun titre audio à modifier dans ce dossier.", parent=dialog_parent)
            return
        if not messagebox.askyesno(
            "Appliquer les règles de titre",
            f"Modifier le nom de {len(changes)} fichier(s) audio dans ce dossier ?",
            parent=dialog_parent,
        ):
            return
        renamed = 0
        for source, title in changes:
            destination = source.with_name(f"{title}{source.suffix}")
            if destination.exists():
                number = 1
                while True:
                    candidate = source.with_name(f"{title} ({number}){source.suffix}")
                    if not candidate.exists():
                        destination = candidate
                        break
                    number += 1
            try:
                source.rename(destination)
                renamed += 1
            except OSError as error:
                self._log(f"Impossible de renommer {source.name} : {error}")
        messagebox.showinfo("Titres", f"{renamed} fichier(s) renommé(s).", parent=dialog_parent)

    def _on_close(self) -> None:
        if self.after_id:
            try:
                self.after_cancel(self.after_id)
            except tk.TclError:
                pass
        self.destroy()
