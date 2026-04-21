import os
import time
import base64
from google import genai
from google.genai import types

_client = None


def get_client():
    global _client
    if _client is None:
        key = os.environ.get("GEMINI_API_KEY", "")
        _client = genai.Client(api_key=key)
    return _client


def generate_keyframe(prompt: str, ref_image_bytes: bytes | None = None,
                      ref_image_mime: str = "image/png") -> bytes:
    """Generate a keyframe image using Nano Banana 2.
    If ref_image_bytes provided, uses it as visual reference for the generation."""
    client = get_client()

    if ref_image_bytes:
        # Send reference image + prompt → Nano Banana generates inspired keyframe
        contents = [
            types.Part(
                inline_data=types.Blob(
                    mime_type=ref_image_mime,
                    data=ref_image_bytes,
                )
            ),
            types.Part(text=(
                f"Using this image as a visual reference for style, subject, and composition, "
                f"generate a new cinematic keyframe image based on this description: {prompt}"
            )),
        ]
    else:
        contents = [f"Generate a cinematic keyframe image: {prompt}"]

    response = client.models.generate_content(
        model="gemini-3.1-flash-image-preview",
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        ),
    )

    # Extract image bytes from response
    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.mime_type.startswith("image/"):
            return part.inline_data.data

    raise Exception("لم يتم توليد صورة")


def submit_video(
    prompt: str,
    image_bytes: bytes | None = None,
    image_mime: str = "image/png",
    model: str = "veo-3.1-fast-generate-preview",
    duration: str = "5",
    aspect_ratio: str = "16:9",
) -> dict:
    """Submit video generation to Veo 3.1."""
    client = get_client()

    kwargs = {
        "model": model,
        "prompt": prompt,
        "config": types.GenerateVideosConfig(aspect_ratio=aspect_ratio),
    }

    if image_bytes:
        # Ensure bytes not string
        if isinstance(image_bytes, str):
            image_bytes = base64.b64decode(image_bytes)
        kwargs["image"] = types.Image(
            image_bytes=image_bytes,
            mime_type=image_mime,
        )

    operation = client.models.generate_videos(**kwargs)

    # Extract operation name — handle different return types
    op_name = ""
    if hasattr(operation, 'name'):
        op_name = operation.name
    elif isinstance(operation, dict):
        op_name = operation.get("name", str(operation))
    else:
        # Try to get any useful identifier
        for attr in ('operation_name', 'id', '_operation_name'):
            if hasattr(operation, attr):
                op_name = getattr(operation, attr)
                break
        if not op_name:
            op_name = repr(operation)[:200]

    return {
        "operation_name": op_name,
        "model": model,
    }


def check_video_status(operation_name: str) -> dict:
    """Check Veo video generation status."""
    client = get_client()

    try:
        # SDK expects object with .name, not a raw string
        op_ref = type('_Op', (), {'name': operation_name})()
        operation = client.operations.get(operation=op_ref)

        if not operation.done:
            return {"status": "processing", "progress": 50}

        # Done — extract video
        response = operation.response
        if not response or not hasattr(response, 'generated_videos') or not response.generated_videos:
            error = getattr(operation, "error", None)
            return {"status": "error", "error": str(error) if error else "فشل التوليد"}

        video_entry = response.generated_videos[0]
        video_file = video_entry.video
        video_bytes = b""
        video_url = None

        # Method 1: save to temp file then read bytes
        try:
            import tempfile
            tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
            tmp_path = tmp.name
            tmp.close()
            client.files.download(file=video_file)
            video_file.save(tmp_path)
            with open(tmp_path, "rb") as f:
                video_bytes = f.read()
            import os
            os.remove(tmp_path)
        except Exception:
            pass

        # Method 2: try direct download if save failed
        if not video_bytes:
            try:
                dl = client.files.download(file=video_file)
                if isinstance(dl, bytes):
                    video_bytes = dl
            except Exception:
                pass

        # Method 3: get URI as fallback
        if not video_bytes:
            if isinstance(video_file, str):
                video_url = video_file
            elif hasattr(video_file, 'uri') and video_file.uri:
                video_url = video_file.uri
            # Try downloading URI with httpx
            if video_url:
                try:
                    import httpx
                    api_key = os.environ.get("GEMINI_API_KEY", "")
                    r = httpx.get(f"{video_url}?key={api_key}", timeout=30, follow_redirects=True)
                    if r.status_code == 200 and len(r.content) > 1000:
                        video_bytes = r.content
                except Exception:
                    pass

        return {
            "status": "done",
            "video_url": video_url,
            "video_bytes": video_bytes,
            "progress": 100,
        }

    except Exception as e:
        import traceback
        return {
            "status": "error",
            "error": f"{str(e)[:150]}\n{traceback.format_exc()[-200:]}",
        }
