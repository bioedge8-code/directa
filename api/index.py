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


# ── URL Reference (direct video URL) ─────────────────────────

class URLRefRequest(BaseModel):
    url: str
    session_id: str
    purpose: str = "camera"

@app.post("/api/url-reference")
async def api_url_reference(req: URLRefRequest):
    import httpx

    # Download the file via HTTP
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            resp = await client.get(req.url)
            resp.raise_for_status()
    except Exception as e:
        raise HTTPException(400, f"فشل تحميل الرابط: {str(e)[:100]}")

    video_bytes = resp.content

    # Max 50MB
    if len(video_bytes) > 50 * 1024 * 1024:
        raise HTTPException(400, "الملف كبير جداً. الحد الأقصى 50MB.")

    # Detect file type from URL extension or content-type
    ct = resp.headers.get("content-type", "").lower()
    url_lower = req.url.lower().split("?")[0]

    ext = "mp4"
    if url_lower.endswith(".webm") or "webm" in ct:
        ext = "webm"
    elif url_lower.endswith(".mov") or "quicktime" in ct:
        ext = "mov"
    elif url_lower.endswith(".mp4") or "mp4" in ct:
        ext = "mp4"

    # Validate: check magic bytes to ensure it's a real video file
    # MP4/MOV start with 'ftyp' at byte 4, WebM starts with 0x1A45DFA3
    head = video_bytes[:12]
    is_mp4 = b'ftyp' in head
    is_webm = head[:4] == b'\x1a\x45\xdf\xa3'
    is_avi = head[:4] == b'RIFF' and b'AVI' in head[:12]

    if not (is_mp4 or is_webm or is_avi):
        # Check if it's HTML (common mistake)
        if video_bytes[:100].lstrip().startswith((b'<', b'<!', b'{', b'[')):
            raise HTTPException(400, "الرابط يشير إلى صفحة ويب وليس ملف فيديو مباشر. استخدم رابط ينتهي بـ .mp4")
        raise HTTPException(400, "الملف ليس بتنسيق فيديو مدعوم (MP4/WebM/AVI)")

    url = upload_reference(video_bytes, f"url_ref.{ext}", ct or "video/mp4",
                           req.session_id, req.purpose)

    return {"url": url, "purpose": req.purpose, "file_type": ext}


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
    duration: str = "5"
    aspect_ratio: str = "16:9"
    resolution: str = "720p"

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

    # Collect reference URLs as lists (reference-to-video accepts arrays)
    image_types = ("png", "jpg", "jpeg", "webp")
    video_types = ("mp4", "mov", "webm")
    audio_types = ("mp3", "wav", "m4a")

    ref_image_urls = []
    ref_video_urls = []
    ref_audio_urls = []
    for ref in req.references:
        url = ref.get("url")
        ft = ref.get("file_type", "")
        if not url:
            continue
        if ft in image_types:
            ref_image_urls.append(url)
        elif ft in video_types:
            ref_video_urls.append(url)
        elif ft in audio_types:
            ref_audio_urls.append(url)

    try:
        fal_result = submit_generation(
            english_prompt=req.english_prompt,
            ref_image_urls=ref_image_urls or None,
            ref_video_urls=ref_video_urls or None,
            ref_audio_urls=ref_audio_urls or None,
            duration=req.duration,
            aspect_ratio=req.aspect_ratio,
            resolution=req.resolution,
        )
        update_generation(generation_id, {
            "status": "processing",
            "fal_request_id": fal_result["request_id"],
            "thumbnail_url": fal_result["model"],
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

    # Use saved model, or determine from references
    model = gen.get("thumbnail_url") or "bytedance/seedance-2.0/fast/text-to-video"
    if model and not model.startswith("bytedance"):
        model = "bytedance/seedance-2.0/fast/text-to-video"
        refs = gen.get("references") or []
        for ref in refs:
            if ref.get("purpose") == "character" and ref.get("file_type") in ("png", "jpg", "jpeg", "webp"):
                model = "bytedance/seedance-2.0/fast/image-to-video"
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
