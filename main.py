"""Démarre le serveur FastAPI local et l’interface CustomTkinter."""
from __future__ import annotations

import threading
import time
import tkinter as tk
from tkinter import messagebox

import uvicorn

from app.api import create_app
from app.config import SettingsStore
from app.downloads import DownloadManager
from app.ui import SonoreApp

HOST = "127.0.0.1"
PORT = 8765


class LocalServer:
    def __init__(self, settings: SettingsStore, host: str = HOST, port: int = PORT) -> None:
        self.host, self.port = host, port
        self.server = uvicorn.Server(uvicorn.Config(create_app(settings, DownloadManager(settings)), host=host, port=port, log_config=None, log_level="critical", access_log=False, lifespan="off", ws="none"))
        self.thread = threading.Thread(target=self.server.run, name="sonore-local-api", daemon=True)

    def start(self, timeout: float = 8.0) -> bool:
        self.thread.start()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.server.started:
                return True
            if not self.thread.is_alive():
                return False
            time.sleep(0.05)
        return self.server.started

    def stop(self) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=3)


def main() -> None:
    settings = SettingsStore()
    server = LocalServer(settings)
    try:
        if not server.start():
            try:
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror("Sonore", f"Impossible de démarrer le serveur local sur {HOST}:{PORT}. Vérifiez que le port n’est pas déjà utilisé.")
                root.destroy()
            except tk.TclError:
                print(f"Impossible de démarrer le serveur local sur {HOST}:{PORT}.")
            return
        app = SonoreApp(settings)
        app.mainloop()
    except tk.TclError as error:
        print(f"Impossible d’ouvrir l’interface graphique : {error}")
    finally:
        server.stop()


if __name__ == "__main__":
    main()
