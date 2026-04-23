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
from lib.director_chat import chat_stream, parse_response
from lib.fal_client import submit_generation as fal_submit, check_status as fal_check
from lib.google_client import generate_keyframe, submit_video as veo_submit, check_video_status as veo_check
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


# ── Auth Config ──────────────────────────────────────────────

@app.get("/api/auth-config")
async def api_auth_config():
    url = os.environ.get("SUPABASE_URL", "")
    anon_key = os.environ.get("SUPABASE_ANON_KEY", "")
    if not url or not anon_key:
        raise HTTPException(404, "Auth not configured")
    return {"url": url, "anon_key": anon_key}


# ── Director Chat (Streaming) ─────────────────────────────────

from fastapi.responses import StreamingResponse
import json as _json

class ChatRequest(BaseModel):
    messages: list

@app.post("/api/chat/stream")
async def api_chat_stream(req: ChatRequest):
    def event_stream():
        full_text = ""
        try:
            for chunk in chat_stream(req.messages):
                if isinstance(chunk, dict) and "__done__" in chunk:
                    # Parse the full response for structured data
                    parsed = parse_response(full_text)
                    # Generate preview images if requested
                    preview_urls = []
                    for pv in parsed.get("previews", []):
                        try:
                            img_bytes = generate_keyframe(pv["prompt"])
                            import base64
                            b64 = base64.b64encode(img_bytes).decode()
                            preview_urls.append({
                                "data": f"data:image/png;base64,{b64}",
                                "purpose": pv.get("purpose", ""),
                            })
                        except Exception:
                            pass

                    yield f"data: {_json.dumps({'type': 'done', 'ready': parsed.get('ready'), 'previews': preview_urls, 'usage': chunk['usage']})}\n\n"
                else:
                    full_text += chunk
                    yield f"data: {_json.dumps({'type': 'text', 'text': chunk})}\n\n"
        except Exception as e:
            yield f"data: {_json.dumps({'type': 'error', 'error': str(e)[:200]})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

# Non-streaming fallback
@app.post("/api/chat")
async def api_chat(req: ChatRequest):
    try:
        full_text = ""
        usage = {}
        for chunk in chat_stream(req.messages):
            if isinstance(chunk, dict) and "__done__" in chunk:
                usage = chunk["usage"]
            else:
                full_text += chunk
        parsed = parse_response(full_text)
        return {
            "message": parsed["display_text"],
            "ready": parsed.get("ready"),
            "usage": usage,
        }
    except Exception as e:
        raise HTTPException(500, f"خطأ في المحادثة: {str(e)[:200]}")


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
    duration: str = "5"
    aspect_ratio: str = "16:9"
    resolution: str = "720p"
    provider: str = "seedance"  # "seedance" or "veo"
    veo_model: str = "veo-3.1-fast-generate-preview"

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

    # Collect reference URLs
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
        if req.provider == "veo":
            # ── Veo 3.1 + Nano Banana 2 pipeline ─────────
            # Always generate keyframe with Nano Banana 2 first
            # If reference image exists → use it as inspiration source
            ref_bytes = None
            ref_mime = "image/png"

            if ref_image_urls:
                # Download reference image to feed to Nano Banana
                import httpx
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.get(ref_image_urls[0])
                    ref_bytes = resp.content
                    ref_mime = resp.headers.get("content-type", "image/png").split(";")[0]

            # Nano Banana 2 generates the keyframe (with or without reference)
            try:
                image_bytes = generate_keyframe(
                    req.english_prompt,
                    ref_image_bytes=ref_bytes,
                    ref_image_mime=ref_mime,
                )
                image_mime = "image/png"
            except Exception as e:
                if ref_bytes:
                    # Fallback: use reference image directly
                    image_bytes = ref_bytes
                    image_mime = ref_mime
                else:
                    image_bytes = None
                    image_mime = "image/png"

            result = veo_submit(
                prompt=req.english_prompt,
                image_bytes=image_bytes,
                image_mime=image_mime,
                model=req.veo_model,
                duration=req.duration,
                aspect_ratio=req.aspect_ratio,
            )
            update_generation(generation_id, {
                "status": "processing",
                "fal_request_id": result["operation_name"],
                "thumbnail_url": "veo:" + result["model"],
            })
            return {
                "generation_id": generation_id,
                "fal_request_id": result["operation_name"],
                "model": result["model"],
            }

        else:
            # ── Seedance 2.0 (fal.ai) ────────────────────
            result = fal_submit(
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
                "fal_request_id": result["request_id"],
                "thumbnail_url": result["model"],
            })
            return {
                "generation_id": generation_id,
                "fal_request_id": result["request_id"],
                "model": result["model"],
            }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        update_generation(generation_id, {"status": "error"})
        raise HTTPException(500, f"فشل إرسال التوليد: {str(e)}\n\n{tb}")


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

    request_id = gen.get("fal_request_id")
    if not request_id:
        return {"status": gen["status"], "progress": 0}

    saved_model = gen.get("thumbnail_url") or ""
    is_veo = saved_model.startswith("veo:")

    if is_veo:
        # ── Veo 3.1 status ────────────────────────────
        result = veo_check(request_id)

        if result["status"] == "done":
            video_bytes = result.get("video_bytes", b"")
            video_url = result.get("video_url")

            # Always upload to Supabase — Google URLs need auth
            if video_bytes:
                video_url = upload_reference(
                    video_bytes, "veo_output.mp4", "video/mp4",
                    gen.get("session_id", "unknown"), "output"
                )

            if video_url:
                update_generation(generation_id, {
                    "status": "done",
                    "video_url": video_url,
                })
            result["video_url"] = video_url
            result.pop("video_bytes", None)

        if result["status"] == "error":
            update_generation(generation_id, {"status": "error"})

        return result

    else:
        # ── Seedance (fal.ai) status ──────────────────
        model = saved_model or "bytedance/seedance-2.0/fast/text-to-video"
        result = fal_check(model, request_id)

        if result["status"] == "done" and result.get("video_url"):
            update_generation(generation_id, {
                "status": "done",
                "video_url": result["video_url"],
            })

        if result["status"] == "error":
            update_generation(generation_id, {"status": "error"})

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
