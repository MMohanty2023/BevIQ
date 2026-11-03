from io import BytesIO
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import app


def test_chat_rejects_unsupported_upload_before_processing():
    response = app.test_client().post(
        "/api/chat",
        data={
            "message": "read this",
            "session_id": "upload-test",
            "file": (BytesIO(b"bad"), "malware.exe"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert "supported uploads" in response.get_json()["error"].lower()
