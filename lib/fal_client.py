import os
import fal_client


def _ensure_key():
    key = os.environ.get("FAL_KEY", "")
    if key:
        os.environ["FAL_KEY"] = key


def submit_generation(
    english_prompt: str,
    ref_image_urls: list[str] | None = None,
    ref_video_urls: list[str] | None = None,
    ref_audio_urls: list[str] | None = None,
    end_image_url: str | None = None,
    duration: str = "5",
    aspect_ratio: str = "16:9",
    resolution: str = "720p",
    generate_audio: bool = True,
    seed: int | None = None,
) -> dict:
    _ensure_key()

    has_videos = ref_video_urls and len(ref_video_urls) > 0
    has_images = ref_image_urls and len(ref_image_urls) > 0
    has_audio = ref_audio_urls and len(ref_audio_urls) > 0

    # ── Model selection ───────────────────────────────────────
    # reference-to-video: accepts lists of images, videos, audio
    # image-to-video: single image_url + optional end_image_url
    # text-to-video: prompt only

    if has_videos or has_audio:
        # reference-to-video accepts all reference types as lists
        model = "bytedance/seedance-2.0/fast/reference-to-video"
        arguments = {
            "prompt": english_prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "generate_audio": generate_audio,
        }
        if has_video_urls := ref_video_urls:
            arguments["video_urls"] = has_video_urls
        if has_images:
            arguments["image_urls"] = ref_image_urls
        if has_audio:
            arguments["audio_urls"] = ref_audio_urls

    elif has_images:
        model = "bytedance/seedance-2.0/fast/image-to-video"
        arguments = {
            "prompt": english_prompt,
            "image_url": ref_image_urls[0],
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "generate_audio": generate_audio,
        }
        if end_image_url:
            arguments["end_image_url"] = end_image_url

    else:
        model = "bytedance/seedance-2.0/fast/text-to-video"
        arguments = {
            "prompt": english_prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "generate_audio": generate_audio,
        }

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
