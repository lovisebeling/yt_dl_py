"""Start the local FastAPI server and the CustomTkinter interface."""
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
                messagebox.showerror("Sonore", f"Could not start the local server at {HOST}:{PORT}. Check that the port is not already in use.")
                root.destroy()
            except tk.TclError:
                print(f"Could not start the local server at {HOST}:{PORT}.")
            return
        app = SonoreApp(settings)
        app.mainloop()
    except tk.TclError as error:
        print(f"Could not open the graphical interface: {error}")
    finally:
        server.stop()


if __name__ == "__main__":
    main()
