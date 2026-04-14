import os
import re
import uuid
from datetime import datetime
from supabase import create_client, Client

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_KEY"]
        _client = create_client(url, key)
    return _client


def get_bucket() -> str:
    return os.environ.get("SUPABASE_STORAGE_BUCKET", "references")


def _safe_filename(filename: str) -> str:
    name, _, ext = filename.rpartition(".")
    if not name:
        name = filename
        ext = ""
    # Keep only ASCII alphanumeric, dashes, underscores
    name = re.sub(r'[^a-zA-Z0-9_-]', '', name) or "file"
    return f"{name}.{ext}" if ext else name


def upload_reference(file_bytes: bytes, filename: str, content_type: str,
                     session_id: str, purpose: str) -> str:
    client = get_client()
    bucket = get_bucket()
    ts = int(datetime.utcnow().timestamp())
    safe_name = _safe_filename(filename)
    path = f"{session_id}/{purpose}/{ts}_{safe_name}"
    client.storage.from_(bucket).upload(
        path, file_bytes,
        file_options={"content-type": content_type, "x-upsert": "true"}
    )
    public_url = client.storage.from_(bucket).get_public_url(path)
    return public_url


def create_generation(generation_id: str, session_id: str, wizard_data: dict,
                      arabic_prompt: str, english_prompt: str,
                      references: list) -> dict:
    client = get_client()
    row = {
        "id": generation_id,
        "session_id": session_id,
        "wizard_data": wizard_data,
        "arabic_prompt": arabic_prompt,
        "english_prompt": english_prompt,
        "references": references,
        "status": "pending",
    }
    result = client.table("generations").insert(row).execute()
    return result.data[0] if result.data else row


def update_generation(generation_id: str, updates: dict) -> dict:
    client = get_client()
    result = (client.table("generations")
              .update(updates)
              .eq("id", generation_id)
              .execute())
    return result.data[0] if result.data else updates


def get_generation(generation_id: str) -> dict | None:
    client = get_client()
    result = (client.table("generations")
              .select("*")
              .eq("id", generation_id)
              .single()
              .execute())
    return result.data


def list_generations(limit: int = 20) -> list:
    client = get_client()
    result = (client.table("generations")
              .select("*")
              .order("created_at", desc=True)
              .limit(limit)
              .execute())
    return result.data or []


def delete_generation(generation_id: str) -> None:
    client = get_client()
    gen = get_generation(generation_id)
    if gen and gen.get("references"):
        bucket = get_bucket()
        for ref in gen["references"]:
            url = ref.get("url", "")
            # Extract storage path from public URL
            marker = f"/object/public/{bucket}/"
            if marker in url:
                path = url.split(marker, 1)[1]
                try:
                    client.storage.from_(bucket).remove([path])
                except Exception:
                    pass
    client.table("generations").delete().eq("id", generation_id).execute()
