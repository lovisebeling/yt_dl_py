"""Local FastAPI API for the interface and download jobs."""
from __future__ import annotations

import asyncio
import queue
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.config import SettingsStore
from app.downloads import DownloadManager


class DownloadRequest(BaseModel):
    url: str = Field(min_length=8, max_length=4096)
    output_dir: str = Field(min_length=1, max_length=4096)
    mode: str = Field(pattern=r"^(single|from_video)$")


def create_app(settings: SettingsStore, downloads: DownloadManager | None = None) -> FastAPI:
    manager = downloads or DownloadManager(settings)
    api = FastAPI(title="Sonore Local API", docs_url=None, redoc_url=None, openapi_url=None)
    api.state.download_manager = manager
    api.state.settings_store = settings

    @api.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @api.get("/settings")
    async def get_settings() -> dict[str, Any]:
        return settings.load()

    @api.put("/settings")
    async def put_settings(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return settings.save(payload)
        except OSError as error:
            raise HTTPException(status_code=500, detail=f"Could not save settings: {error}") from error

    @api.post("/downloads", status_code=202)
    async def start_download(request: DownloadRequest) -> dict[str, str]:
        try:
            job = manager.start(request.url.strip(), request.output_dir, request.mode)
            return {"job_id": job.job_id, "state": job.state}
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @api.get("/downloads/{job_id}")
    async def job_state(job_id: str) -> dict[str, Any]:
        job = manager.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Download not found.")
        return {"job_id": job.job_id, "state": job.state}

    @api.get("/downloads/{job_id}/events")
    async def job_events(job_id: str) -> dict[str, Any]:
        job = manager.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Download not found.")
        events: list[dict[str, Any]] = []
        for _ in range(100):
            try:
                events.append(job.events.get_nowait())
            except queue.Empty:
                break
        await asyncio.sleep(0)
        return {"events": events}

    return api
