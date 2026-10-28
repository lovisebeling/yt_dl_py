"""Construit Sonore.exe sur Windows avec PyInstaller."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
import tkinter

ROOT = Path(__file__).resolve().parent.parent


def _copy_virtual_tree(interpreter, source: str, destination: Path) -> None:
    """Extrait les bibliothèques Tcl/Tk intégrées dans le zipfs de Python 3.14."""
    destination.mkdir(parents=True, exist_ok=True)
    for entry in interpreter.call("glob", "-nocomplain", "-directory", source, "*"):
        relative = str(entry)[len(source):].lstrip("/")
        target = destination.joinpath(*relative.split("/"))
        if interpreter.call("file", "isdirectory", entry):
            _copy_virtual_tree(interpreter, str(entry), target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            interpreter.call("file", "copy", "-force", entry, str(target.resolve()))


def _collect_zipfs_tk(args: list[str], temp_dir: Path) -> None:
    """PyInstaller ne sait pas lire les ressources Tk de Python 3.14 depuis zipfs."""
    import tkinter

    root = tkinter.Tk()
    root.withdraw()
    try:
        tcl_source = str(root.tk.eval("info library"))
        tk_source = str(root.tk.eval("set tk_library"))
        if not (tcl_source.startswith("//zipfs:") and tk_source.startswith("//zipfs:")):
            return
        tcl_dest, tk_dest = temp_dir / "tcl", temp_dir / "tk"
        _copy_virtual_tree(root.tk, tcl_source, tcl_dest)
        _copy_virtual_tree(root.tk, tk_source, tk_dest)
        args.extend(["--add-data", f"{tcl_dest}{os.pathsep}_tcl_data", "--add-data", f"{tk_dest}{os.pathsep}_tk_data"])
        print("Bibliothèques Tcl/Tk extraites du zipfs de Python et incluses dans le build.")
    finally:
        root.destroy()


def main() -> int:
    if sys.platform != "win32":
        print("Le build PyInstaller est prévu pour Windows. Lancez ce script sous Windows.", file=sys.stderr)
        return 2
    executable = sys.executable
    args = [executable, "-m", "PyInstaller", "--noconfirm", "--windowed", "--onedir", "--name", "Sonore", "--collect-all", "customtkinter", "--collect-all", "yt_dlp", "--collect-all", "uvicorn", "--collect-submodules", "fastapi", "--hidden-import", "uvicorn.logging", "--hidden-import", "uvicorn.loops.auto", "--hidden-import", "uvicorn.protocols.http.auto"]
    tk_temp = ROOT / ".sonore-tk-data"
    if tk_temp.exists():
        shutil.rmtree(tk_temp)
    tk_temp.mkdir()
    try:
        try:
            _collect_zipfs_tk(args, tk_temp)
        except tkinter.TclError as error:
            print(f"Impossible d’extraire les données Tcl/Tk intégrées : {error}", file=sys.stderr)
            return 1
        args.append(str(ROOT / "main.py"))
        ffmpeg = ROOT / "tools" / "ffmpeg" / "ffmpeg.exe"
        if ffmpeg.is_file():
            args.extend(["--add-binary", f"{ffmpeg}{os.pathsep}tools/ffmpeg"])
        completed = subprocess.run(args, cwd=ROOT, check=False)
    finally:
        shutil.rmtree(tk_temp, ignore_errors=True)
    if completed.returncode == 0:
        app_dir = ROOT / "dist" / "Sonore"
        if not (app_dir / "Sonore.exe").is_file():
            print(f"Build réussi, mais exécutable introuvable dans {app_dir}.", file=sys.stderr)
            return 1
        archive = ROOT / "dist" / "Sonore-windows-x64.zip"
        if archive.exists():
            archive.unlink()
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as package:
            for path in sorted(app_dir.rglob("*")):
                if not path.is_file() or path.name == "settings.json":
                    continue
                package.write(path, Path("Sonore") / path.relative_to(app_dir))
        if ffmpeg.is_file():
            print("FFmpeg a été inclus dans le dossier de l’application.")
        else:
            print("FFmpeg non inclus : Sonore utilisera FFmpeg installé dans le PATH.")
        print(f"Application construite : {app_dir / 'Sonore.exe'}")
        print(f"Paquet prêt pour une release GitHub : {archive}")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
