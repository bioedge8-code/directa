import os
import fal_client


def _ensure_key():
    key = os.environ.get("FAL_KEY", "")
    if key:
        os.environ["FAL_KEY"] = key


def submit_generation(english_prompt: str, ref_character_url: str | None = None,
                      ref_audio_url: str | None = None,
                      duration: int = 5, aspect_ratio: str = "16:9") -> dict:
    _ensure_key()

    if ref_character_url:
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

    # Add audio reference if provided
    if ref_audio_url:
        arguments["audio_url"] = ref_audio_url

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
