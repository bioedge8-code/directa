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


# ── YouTube Reference ─────────────────────────────────────────

class YouTubeRequest(BaseModel):
    url: str
    session_id: str
    purpose: str = "camera"

@app.post("/api/youtube-reference")
async def api_youtube_reference(req: YouTubeRequest):
    import tempfile
    import subprocess
    from pytubefix import YouTube

    try:
        yt = YouTube(req.url)
    except Exception:
        raise HTTPException(400, "رابط يوتيوب غير صالح")

    # Get lowest resolution stream (fastest download)
    stream = (
        yt.streams
        .filter(progressive=True, file_extension="mp4")
        .order_by("resolution")
        .first()
    )
    if not stream:
        raise HTTPException(400, "لا يوجد stream متاح لهذا الفيديو")

    # Download full video to temp
    dl_path = stream.download(output_path="/tmp", filename=f"yt_{req.session_id[:8]}.mp4")

    # Trim to max 15 seconds using ffmpeg (save only the trimmed version)
    trimmed_path = f"/tmp/yt_trimmed_{req.session_id[:8]}.mp4"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", dl_path, "-t", "15", "-c", "copy", trimmed_path],
            capture_output=True, timeout=30,
        )
        with open(trimmed_path, "rb") as f:
            video_bytes = f.read()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # ffmpeg not available — use full file but reject if too long
        if yt.length and yt.length > 15:
            raise HTTPException(400, f"الفيديو طويل ({yt.length}ث). الحد 15 ثانية. ثبّت ffmpeg أو اختر مقطع أقصر.")
        with open(dl_path, "rb") as f:
            video_bytes = f.read()
    finally:
        # Cleanup temp files
        import os as _os
        for p in (dl_path, trimmed_path):
            try:
                _os.remove(p)
            except OSError:
                pass

    if len(video_bytes) > 50 * 1024 * 1024:
        raise HTTPException(400, "الملف كبير جداً بعد القص. الحد الأقصى 50MB.")

    url = upload_reference(video_bytes, "yt_ref.mp4", "video/mp4",
                           req.session_id, req.purpose)

    return {"url": url, "purpose": req.purpose, "file_type": "mp4"}


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
