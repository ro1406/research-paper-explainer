# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
FastAPI entrypoint for an ADK agent using **in-memory** session and artifact storage.

Intended for **single-instance** deployment (e.g. one Cloud Run instance with min/max
instances = 1). State is lost on restart and is not shared across replicas.

Swap points for your project:
  - Import: replace `paper_agent` / the fallback import with your real agent symbol
    (this repo exposes `root_agent` in `research_explainer.agent`).

Images in the JSON response are **data URLs** (`data:image/png;base64,...`) loaded from
the in-memory artifact store after the run, so a browser or frontend can render them
without GCS.

Session TTL: set ``SESSION_TTL_SECONDS`` (seconds of inactivity). ``0`` disables expiry.
After TTL, the session is deleted and recreated on the next request. Only **session-scoped**
artifacts are removed on expiry; ``user:`` namespaced artifacts are left intact so other
sessions for the same ``user_id`` are not affected.
"""

from __future__ import annotations

import base64
import logging
import os
import time
from typing import Any, Iterable

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from google.adk.artifacts import InMemoryArtifactService
from google.adk.events.event import Event
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import BaseModel
import uvicorn

# -----------------------------------------------------------------------------
# SWAP: import your root ADK agent here.
# Example for this repository:
#   from research_explainer.agent import root_agent as paper_agent
# -----------------------------------------------------------------------------
try:
    from agent import paper_agent
except ImportError:  # pragma: no cover - convenience for this repo layout
    from research_explainer.agent import root_agent as paper_agent

logger = logging.getLogger(__name__)

# Max PDF size for UploadFile (bytes).
MAX_PDF_BYTES = int(os.environ.get("MAX_PDF_BYTES", str(25 * 1024 * 1024)))

APP_NAME = os.environ.get("ADK_APP_NAME", "research_explainer")
DEFAULT_USER_ID = os.environ.get("ADK_USER_ID", "web")
# Set RUNNING_LOCALLY=1 for verbose session logging (similar to local dev flags).
RUNNING_LOCALLY = os.environ.get("RUNNING_LOCALLY", "").lower() in (
    "1",
    "true",
    "yes",
)

artifact_service = InMemoryArtifactService()
session_service = InMemorySessionService()

runner = Runner(
    app_name=APP_NAME,
    agent=paper_agent,
    session_service=session_service,
    artifact_service=artifact_service,
    # Session is created explicitly in `resolve_session` before each run.
    auto_create_session=False,
)


async def resolve_session(
    user_id: str,
    session_id: str,
    *,
    initial_state: dict[str, Any] | None = None,
) -> None:
    """
    Load an existing session or create one with the given id.

    Use `initial_state` when you need to seed session-scoped state on first creation
    (e.g. tool flags). Omitted here by default; extend the call site if your app needs it.
    """
    sess = await session_service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )
    if sess is not None:
        if RUNNING_LOCALLY:
            logger.info(
                "Session already exists: app=%r user=%r session=%r",
                APP_NAME,
                user_id,
                session_id,
            )
        return

    await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
        state=initial_state,
    )
    logger.info(
        "New session created: app=%r user=%r session=%r",
        APP_NAME,
        user_id,
        session_id,
    )


app = FastAPI(title="Research Explainer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _gather_text_for_response(events: Iterable[Event]) -> str:
    """Collects user-visible assistant text from streamed events.

    Do not skip events just because they also include tool calls/responses; the model
    often emits explanation text in the same turn as ``function_call`` parts. Skipping
    those events previously dropped the entire explanation while images still appeared.
    """
    final_chunks: list[str] = []
    assistant_chunks: list[str] = []

    for event in events:
        if event.partial:
            continue
        if not event.content or not event.content.parts:
            continue
        # User turn events can appear in the stream; only aggregate assistant output.
        if event.author == "user":
            continue

        pieces: list[str] = []
        for part in event.content.parts:
            if part.text:
                pieces.append(part.text)
        segment = "".join(pieces).strip()
        if not segment:
            continue

        assistant_chunks.append(segment)
        if event.is_final_response():
            final_chunks.append(segment)

    if final_chunks:
        return "\n\n".join(final_chunks)
    if assistant_chunks:
        return "\n\n".join(assistant_chunks)
    return ""


async def _collect_images_as_data_urls(
    events: Iterable[Event],
    *,
    app_name: str,
    user_id: str,
    session_id: str,
) -> list[str]:
    """
    Loads image artifacts touched during this run from the in-memory artifact service
    and returns them as data URLs for the frontend.
    """
    seen: set[tuple[str, int]] = set()
    ordered: list[str] = []

    for event in events:
        if not event.actions or not event.actions.artifact_delta:
            continue
        for filename, version in event.actions.artifact_delta.items():
            key = (filename, version)
            if key in seen:
                continue
            seen.add(key)

            load_session_id = None if filename.startswith("user:") else session_id
            part = await artifact_service.load_artifact(
                app_name=app_name,
                user_id=user_id,
                filename=filename,
                session_id=load_session_id,
                version=version,
            )
            if not part or not part.inline_data or not part.inline_data.data:
                continue
            mime = (part.inline_data.mime_type or "application/octet-stream").lower()
            if not mime.startswith("image/"):
                continue
            b64 = base64.b64encode(part.inline_data.data).decode("ascii")
            ordered.append(f"data:{mime};base64,{b64}")

    return ordered


class ExplainResponse(BaseModel):
    text: str
    images: list[str]


@app.post("/api/explain", response_model=ExplainResponse)
async def explain(
    session_id: str = Form(...),
    user_input: str = Form(""),
    file: UploadFile | None = File(default=None),
) -> ExplainResponse:
    """
    Runs one agent turn for the given ``session_id``.

    Send JSON-compatible fields via **multipart/form-data**: ``session_id``, ``user_input``,
    and optional ``file`` (PDF). The PDF is attached to the user message as inline bytes
    for the model. A PDF is only accepted on the **first** turn of a session (no prior
    events); later turns must omit ``file``.
    """
    session_id = session_id.strip()
    user_input = (user_input or "").strip()
    user_id = DEFAULT_USER_ID

    pdf_bytes: bytes | None = None
    if file is not None and getattr(file, "filename", None):
        if not str(file.filename).lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400, detail="Only PDF uploads are supported (.pdf)."
            )
        pdf_bytes = await file.read()
        if len(pdf_bytes) > MAX_PDF_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"PDF exceeds maximum size of {MAX_PDF_BYTES // (1024 * 1024)} MB.",
            )
        if not pdf_bytes:
            raise HTTPException(status_code=400, detail="Uploaded PDF is empty.")

    if not user_input and not pdf_bytes:
        raise HTTPException(
            status_code=400,
            detail="Provide non-empty user_input and/or a PDF file.",
        )

    try:
        await resolve_session(user_id, session_id)
    except Exception as exc:  # pragma: no cover - runtime guard
        logger.exception("Session resolution failed for session_id=%s", session_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    existing = await session_service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )
    if (
        pdf_bytes is not None
        and existing
        and existing.events
        and len(existing.events) > 0
    ):
        raise HTTPException(
            status_code=400,
            detail="A PDF can only be attached on the first message of a conversation.",
        )

    parts: list[types.Part] = []
    if pdf_bytes is not None:
        parts.append(
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
        )
    if user_input:
        parts.append(types.Part.from_text(text=user_input))

    new_message = types.Content(role="user", parts=parts)

    collected: list[Event] = []

    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=new_message,
        ):
            collected.append(event)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - runtime guard
        logger.exception("Runner failed for session_id=%s", session_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    text = _gather_text_for_response(collected)
    images = await _collect_images_as_data_urls(
        collected,
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )

    return ExplainResponse(text=text, images=images)


if __name__ == "__main__":
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
