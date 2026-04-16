import qrcode
import json
import os
import io
import base64
from datetime import datetime 

QR_DIR = os.path.join(os.path.dirname(__file__), "static", "qr")
os.makedirs(QR_DIR, exist_ok=True)


def _make_qr(data: dict) -> qrcode.image.base.BaseImage:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(json.dumps(data, separators=(",", ":")))
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1a1a2e", back_color="white")
    return img


def generate_student_qr_b64(student_id: int, class_id: int,
                              session_id: int, lat: float, lon: float) -> str:
    """Generate a student QR code and return it as a base-64 PNG string."""
    payload = {
        "type": "student",
        "student_id": student_id,
        "class_id": class_id,
        "session_id": session_id,
        "lat": lat,
        "lon": lon,
        "ts": datetime.utcnow().isoformat(),
    }
    img = _make_qr(payload)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def generate_session_qr_b64(class_id: int, session_id: int) -> str:
    """Generate a class-session QR code (displayed on teacher screen)."""
    payload = {
        "type": "session",
        "class_id": class_id,
        "session_id": session_id,
        "ts": datetime.utcnow().isoformat(),
    }
    img = _make_qr(payload)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")
