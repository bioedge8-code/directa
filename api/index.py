import sys
import os
import uuid

# Add project root to path for lib imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from lib.prompt_builder import build_prompts
from lib.fal_client import submit_generation, check_status
from lib.supabase_client import (
    upload_reference,
    create_generation,
    update_generation,
    get_generation,
    list_generations,
    delete_generation,
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Upload Reference ─────────────────────────────────────────

@app.post("/api/upload-reference")
async def api_upload_reference(
    file: UploadFile = File(...),
    purpose: str = Form(...),
    session_id: str = Form(...),
):
    contents = await file.read()
    max_sizes = {
        "character": 10 * 1024 * 1024,
        "product": 10 * 1024 * 1024,
        "lighting": 10 * 1024 * 1024,
        "camera": 50 * 1024 * 1024,
        "audio": 20 * 1024 * 1024,
    }
    limit = max_sizes.get(purpose, 10 * 1024 * 1024)
    if len(contents) > limit:
        raise HTTPException(400, f"File too large. Max {limit // (1024*1024)}MB.")

    content_type = file.content_type or "application/octet-stream"
    filename = file.filename or "upload"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    url = upload_reference(contents, filename, content_type, session_id, purpose)

    return {"url": url, "purpose": purpose, "file_type": ext}


# ── Build Prompt ─────────────────────────────────────────────

class BuildPromptRequest(BaseModel):
    wizard_data: dict

@app.post("/api/build-prompt")
async def api_build_prompt(req: BuildPromptRequest):
    result = build_prompts(req.wizard_data)
    return {
        "arabic_prompt": result["arabic_prompt"],
        "english_prompt": result["english_prompt"],
        "preview": result["arabic_prompt"][:200],
    }


# ── Generate ─────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    session_id: str
    wizard_data: dict
    english_prompt: str
    arabic_prompt: str
    references: list = []

@app.post("/api/generate")
async def api_generate(req: GenerateRequest):
    generation_id = str(uuid.uuid4())

    create_generation(
        generation_id=generation_id,
        session_id=req.session_id,
        wizard_data=req.wizard_data,
        arabic_prompt=req.arabic_prompt,
        english_prompt=req.english_prompt,
        references=req.references,
    )

    # Determine if we have a character reference image for image-to-video
    ref_char_url = None
    for ref in req.references:
        if ref.get("purpose") == "character" and ref.get("file_type") in ("png", "jpg", "jpeg", "webp"):
            ref_char_url = ref.get("url")
            break

    try:
        fal_result = submit_generation(
            english_prompt=req.english_prompt,
            ref_character_url=ref_char_url,
        )
        update_generation(generation_id, {
            "status": "processing",
            "fal_request_id": fal_result["request_id"],
        })
    except Exception as e:
        update_generation(generation_id, {
            "status": "error",
        })
        raise HTTPException(500, f"Failed to submit to fal.ai: {str(e)}")

    return {
        "generation_id": generation_id,
        "fal_request_id": fal_result["request_id"],
        "model": fal_result["model"],
    }


# ── Status ───────────────────────────────────────────────────

@app.get("/api/status/{generation_id}")
async def api_status(generation_id: str):
    gen = get_generation(generation_id)
    if not gen:
        raise HTTPException(404, "Generation not found")

    if gen["status"] in ("done", "error"):
        return {
            "status": gen["status"],
            "video_url": gen.get("video_url"),
            "progress": 100 if gen["status"] == "done" else 0,
        }

    fal_request_id = gen.get("fal_request_id")
    if not fal_request_id:
        return {"status": gen["status"], "progress": 0}

    # Determine model from wizard_data references
    model = "fal-ai/seedance-1"
    refs = gen.get("references") or []
    for ref in refs:
        if ref.get("purpose") == "character" and ref.get("file_type") in ("png", "jpg", "jpeg", "webp"):
            model = "fal-ai/seedance-1/image-to-video"
            break

    result = check_status(model, fal_request_id)

    if result["status"] == "done" and result.get("video_url"):
        update_generation(generation_id, {
            "status": "done",
            "video_url": result["video_url"],
        })

    if result["status"] == "error":
        update_generation(generation_id, {
            "status": "error",
        })

    return result


# ── History ──────────────────────────────────────────────────

@app.get("/api/history")
async def api_history():
    return list_generations(20)


# ── Delete ───────────────────────────────────────────────────

@app.delete("/api/generation/{generation_id}")
async def api_delete(generation_id: str):
    try:
        delete_generation(generation_id)
    except Exception:
        raise HTTPException(404, "Generation not found")
    return {"ok": True}
