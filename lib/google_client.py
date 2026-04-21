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

    config = {
        "aspect_ratio": aspect_ratio,
    }

    if image_bytes:
        # Image-to-video
        image = types.Image(
            image_bytes=image_bytes,
            mime_type=image_mime,
        )
        operation = client.models.generate_videos(
            model=model,
            prompt=prompt,
            image=image,
            config=types.GenerateVideosConfig(**config),
        )
    else:
        # Text-to-video
        operation = client.models.generate_videos(
            model=model,
            prompt=prompt,
            config=types.GenerateVideosConfig(**config),
        )

    return {
        "operation_name": operation.name,
        "model": model,
    }


def check_video_status(operation_name: str) -> dict:
    """Check Veo video generation status."""
    client = get_client()

    try:
        operation = client.operations.get(operation=operation_name)

        if operation.done:
            if operation.response and operation.response.generated_videos:
                video = operation.response.generated_videos[0]
                # Download video to get URL
                video_data = client.files.download(file=video.video)
                # Return as base64 data URL for now — we'll upload to Supabase
                video_bytes = video_data if isinstance(video_data, bytes) else b""

                # Try to get the video URI
                video_url = None
                if hasattr(video.video, "uri"):
                    video_url = video.video.uri

                return {
                    "status": "done",
                    "video_url": video_url,
                    "video_bytes": video_bytes,
                    "progress": 100,
                }

            error = getattr(operation, "error", None)
            return {
                "status": "error",
                "error": str(error) if error else "فشل التوليد بدون سبب واضح",
            }

        return {
            "status": "processing",
            "progress": 50,
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)[:200],
        }
