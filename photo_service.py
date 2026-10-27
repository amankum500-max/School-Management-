"""
Student photo upload to Supabase Storage.
Handles upload, delete, and URL generation.
"""
import os
import re
import requests
from io import BytesIO

# Lazy import
_supabase_client = None


def _get_supabase():
    global _supabase_client
    if _supabase_client is None:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL", "").strip()
        key = os.getenv("SUPABASE_SERVICE_KEY", "").strip()
        if not url or not key:
            raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_KEY not set")
        _supabase_client = create_client(url, key)
    return _supabase_client


BUCKET = "student-photos"
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


def _safe_filename(student_id, original_name):
    """Unique filename per student"""
    ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else "jpg"
    if ext not in ALLOWED_EXTENSIONS:
        ext = "jpg"
    return f"students/{student_id}.{ext}"


def _guess_content_type(ext):
    return {
        "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "png": "image/png", "webp": "image/webp"
    }.get(ext, "image/jpeg")


def upload_student_photo(student_id, file_storage):
    """
    file_storage: Flask FileStorage object (from request.files['photo'])
    Returns: public URL or None on failure
    """
    if not file_storage or not file_storage.filename:
        return {"ok": False, "error": "No file provided"}

    filename = file_storage.filename
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        return {"ok": False,
                "error": f"Invalid format. Use: {', '.join(ALLOWED_EXTENSIONS)}"}

    # Read file into memory
    file_storage.seek(0)
    file_bytes = file_storage.read()

    if len(file_bytes) > MAX_FILE_SIZE:
        return {"ok": False,
                "error": f"File too large ({len(file_bytes)//1024}KB). Max 2 MB."}

    if len(file_bytes) < 500:
        return {"ok": False, "error": "File too small — invalid image"}

    safe_name = _safe_filename(student_id, filename)
    content_type = _guess_content_type(ext)

    try:
        sb = _get_supabase()

        # Delete old photos (any extension) first
        try:
            existing = sb.storage.from_(BUCKET).list("students")
            for f in existing:
                if f.get("name", "").startswith(f"{student_id}."):
                    sb.storage.from_(BUCKET).remove([f"students/{f['name']}"])
        except Exception:
            pass  # ignore if none exist

        # Upload
        sb.storage.from_(BUCKET).upload(
            path=safe_name,
            file=file_bytes,
            file_options={
                "content-type": content_type,
                "upsert": "true",
                "cache-control": "3600"
            }
        )

        # Get public URL
        url_data = sb.storage.from_(BUCKET).get_public_url(safe_name)
        # supabase-py v1 returns str, v2 returns dict
        if isinstance(url_data, str):
            public_url = url_data
        else:
            public_url = url_data.get("publicURL") or url_data.get("publicUrl") or ""

        if not public_url:
            return {"ok": False, "error": "Could not generate public URL"}

        # Add cache-buster so old photos don't stick
        import time as _t
        public_url = public_url.split("?")[0] + f"?v={int(_t.time())}"

        return {"ok": True, "url": public_url, "path": safe_name}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def delete_student_photo(student_id):
    """Delete all photos for a student"""
    try:
        sb = _get_supabase()
        existing = sb.storage.from_(BUCKET).list("students")
        to_delete = [f"students/{f['name']}" for f in existing
                     if f.get("name", "").startswith(f"{student_id}.")]
        if to_delete:
            sb.storage.from_(BUCKET).remove(to_delete)
        return {"ok": True, "deleted": len(to_delete)}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def is_configured():
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_KEY"))
