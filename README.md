# Sonore

A local Windows app for downloading audio from YouTube videos, converting it to MP3 with FFmpeg, and combining selected playlist tracks into a ZIP archive.

## Requirements

- Windows 10 or 11 and Python 3.10 or later to run from source.
- FFmpeg installed and available on `PATH` when running from source. To bundle it in a build, place `ffmpeg.exe` in `tools/ffmpeg/` before building.
- Follow copyright laws and the terms of service for the content you download.

## Install and run

### Use the Windows release (Python not required)

1. Open **Releases** on the GitHub project page and download `Sonore-windows-x64.zip` from the latest release.
2. Extract the entire archive to a folder you can write to.
3. Run `Sonore/Sonore.exe`. Windows may show a warning because the app is unsigned; make sure the file came from this project's release.

The ZIP contains the complete app folder. Do not move `Sonore.exe` out of that folder. Python is not required. FFmpeg must be installed and available on `PATH` to convert downloads to MP3, unless the release maintainer included it. Settings are stored separately from the app in `%APPDATA%\Sonore\settings.json`.

### Run from source

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

The dark CustomTkinter interface starts a hidden local FastAPI server bound only to `127.0.0.1:8765`. The server shuts down when the window closes.

Paste a YouTube link and click **Download**, or press Enter. Use **Browse** to choose an output folder. The playlist modes are mutually exclusive: **Ignore playlists** downloads only the linked video; **Download this video and the following videos in its playlist** downloads that video and all later tracks. Multiple tracks are combined into a ZIP. Progress and confirmations appear in the built-in console.

In **Settings**, manage text to remove from titles and replacement rules. A replacement can be appended to the end of a title. **Apply to files in a folder…** also renames existing audio files in a selected folder using the saved rules, after confirmation.

## Settings

On Windows, settings are stored in `%APPDATA%\Sonore\settings.json`. On other systems, they use the standard user configuration directory. Settings persist across sessions and app updates, even if the app folder is replaced or removed. On first launch, Sonore automatically copies an older `settings.json` found next to the app or `main.py`. Settings include the output folder, playlist mode, and title rules. To reset them, close Sonore and delete `%APPDATA%\Sonore\settings.json`.

## Build the Windows executable

Build on Windows with Python 3.10 or later. From the repository root:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
# Optional: place ffmpeg.exe in tools/ffmpeg/ to include it in the package.
python scripts/build.py
```

The script builds a 64-bit Windows app in directory mode, then creates `dist/Sonore-windows-x64.zip`. Attach this ZIP to a GitHub Release. It contains the complete `Sonore/` folder and `Sonore.exe`. The executable is also available at `dist/Sonore/Sonore.exe`, but should not be distributed on its own. The ZIP excludes `settings.json` so local build-machine settings are not published. If FFmpeg is not placed in `tools/ffmpeg/`, the app looks for it on the system `PATH`.

The GitHub Actions workflow at `.github/workflows/release.yml` can build the ZIP automatically when a release is published. It can also be run manually from the **Actions** tab; the ZIP will then be available as a downloadable artifact.

## Project structure

```text
main.py                 Starts the interface and local server
app/config.py           JSON settings persistence
app/api.py              Local FastAPI API
app/downloads.py        yt-dlp, progress, MP3 conversion, and ZIP archives
app/ui.py               Dark CustomTkinter interface
app/settings_window.py  Title-rule settings tabs
scripts/build.py        Windows build with PyInstaller
```

## Troubleshooting

- **FFmpeg not found**: install FFmpeg and add its folder to `PATH`, or place `ffmpeg.exe` in `tools/ffmpeg/` before building.
- **YouTube HTTP 403**: yt-dlp versions earlier than `2026.08.19` may fail for some streams. Update the dependencies and rebuild the app. YouTube may also temporarily block an IP address or reject connections through a VPN/proxy; try again later or use another network.
- **Other network errors**: update yt-dlp (`python -m pip install -U yt-dlp`) and check that the content is available.
- **The server does not start**: check that another program is not using `127.0.0.1:8765`.
