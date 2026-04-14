import os
import fal_client

# Negative prompt — always sent to block common AI artifacts
NEGATIVE_PROMPT = (
    "news broadcast, 3d animation, computer graphics, cartoon, childish, "
    "watermark, logo, text, on screen text, subtitles, titles, signature, "
    "hand deformities, finger deformities, unnatural facial expressions, "
    "oversaturated colors, flickering, strobing, morphing, visual glitches, "
    "blurry, low quality, low resolution, pixelated"
)


def _ensure_key():
    key = os.environ.get("FAL_KEY", "")
    if key:
        os.environ["FAL_KEY"] = key


def submit_generation(
    english_prompt: str,
    ref_character_url: str | None = None,
    ref_video_url: str | None = None,
    ref_audio_url: str | None = None,
    duration: int = 5,
    aspect_ratio: str = "16:9",
    seed: int | None = None,
) -> dict:
    _ensure_key()

    # Model selection priority: video ref > image ref > text only
    if ref_video_url and not ref_character_url:
        model = "bytedance/seedance-2.0/fast/reference-to-video"
        arguments = {
            "prompt": english_prompt,
            "reference_video_url": ref_video_url,
            "duration": str(duration),
            "aspect_ratio": aspect_ratio,
        }
    elif ref_character_url:
        model = "bytedance/seedance-2.0/fast/image-to-video"
        arguments = {
            "prompt": english_prompt,
            "image_url": ref_character_url,
            "duration": str(duration),
            "aspect_ratio": aspect_ratio,
        }
    else:
        model = "bytedance/seedance-2.0/fast/text-to-video"
        arguments = {
            "prompt": english_prompt,
            "duration": str(duration),
            "aspect_ratio": aspect_ratio,
        }

    # Add negative prompt
    arguments["negative_prompt"] = NEGATIVE_PROMPT

    # Add audio reference if provided
    if ref_audio_url:
        arguments["audio_url"] = ref_audio_url

    # Add seed for reproducibility
    if seed is not None:
        arguments["seed"] = seed

    handler = fal_client.submit(model, arguments=arguments)

    return {
        "request_id": handler.request_id,
        "model": model,
    }


def check_status(model: str, request_id: str) -> dict:
    _ensure_key()

    try:
        status = fal_client.status(model, request_id, with_logs=True)
        status_type = type(status).__name__

        if status_type == "Completed":
            result = fal_client.result(model, request_id)
            video_url = None
            if isinstance(result, dict):
                video = result.get("video")
                if isinstance(video, dict):
                    video_url = video.get("url")
                elif isinstance(video, str):
                    video_url = video
                if not video_url:
                    video_url = result.get("video_url") or result.get("url")
            return {
                "status": "done",
                "video_url": video_url,
                "progress": 100,
            }

        if status_type == "InProgress":
            logs = []
            if hasattr(status, "logs") and status.logs:
                logs = [l.message if hasattr(l, "message") else str(l)
                        for l in status.logs[-5:]]
            return {
                "status": "processing",
                "progress": getattr(status, "progress", 50) or 50,
                "logs": logs,
            }

        if status_type == "Queued":
            return {
                "status": "processing",
                "progress": 5,
                "position": getattr(status, "position", None),
            }

        return {"status": "processing", "progress": 0}

    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower() or "404" in error_msg:
            return {"status": "error", "error": "Generation not found or expired."}
        return {"status": "error", "error": error_msg}
