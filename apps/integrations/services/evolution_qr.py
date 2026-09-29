"""Normaliza o QR do webhook Evolution-Go para data URI usável em <img src>."""

from __future__ import annotations

import base64
import io
import logging
from typing import Any

import qrcode

logger = logging.getLogger(__name__)

DATA_URI_PREFIX = "data:image/png;base64,"
_PNG_B64_MAGIC = "iVBOR"
_PNG_BYTES_MAGIC = b"\x89PNG"

_IMAGE_KEYS = frozenset(
    {"base64", "qrcodebase64", "image", "qrcode", "qr", "qr_code", "qrimage", "qr_image"}
)
_TEXT_KEYS = frozenset({"code", "pairingcode", "pairing_code", "pairingcodevalue"})


def _kind(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return "empty"
    if text.startswith("data:image/"):
        return "data_uri"
    compact = text.replace("\n", "").replace("\r", "").replace(" ", "")
    if compact.startswith(_PNG_B64_MAGIC):
        return "png_b64"
    lowered = text.lower()
    if text.startswith("2@"):
        return "pairing_2at"
    if "wa.me" in lowered:
        return "wa_me"
    if lowered.startswith("http://") or lowered.startswith("https://"):
        return "url"
    return "other"


def _is_png_bytes(raw: bytes) -> bool:
    return raw.startswith(_PNG_BYTES_MAGIC)


def _decode_b64(value: str) -> bytes:
    compact = value.strip().replace("\n", "").replace("\r", "").replace(" ", "")
    if compact.startswith("data:") and "," in compact:
        compact = compact.split(",", 1)[1]
    padded = compact + "=" * (-len(compact) % 4)
    return base64.b64decode(padded, validate=False)


def _looks_like_png(value: str) -> bool:
    kind = _kind(value)
    if kind == "data_uri":
        try:
            return _is_png_bytes(_decode_b64(value)) or value.startswith("data:image/")
        except Exception:
            return value.startswith("data:image/")
    if kind == "png_b64":
        return True
    try:
        decoded = _decode_b64(value)
    except Exception:
        return False
    return _is_png_bytes(decoded)


def _looks_like_pairing_text(value: str) -> bool:
    kind = _kind(value)
    if kind in {"pairing_2at", "wa_me", "url"}:
        return True
    text = (value or "").strip()
    if "@" in text and "," in text and 16 <= len(text) <= 4096 and not _looks_like_png(text):
        return True
    return False


def _png_to_data_uri(png_bytes: bytes) -> str:
    encoded = base64.b64encode(png_bytes).decode("ascii")
    return f"{DATA_URI_PREFIX}{encoded}"


def _pairing_text_to_data_uri(text: str) -> str:
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=6, border=2)
    qr.add_data(text.strip())
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return _png_to_data_uri(buf.getvalue())


def _to_data_uri_from_png_value(value: str) -> str:
    text = value.strip()
    if text.startswith("data:image/"):
        return text
    return _png_to_data_uri(_decode_b64(text))


def _walk_strings(node: Any, *, prefix: str = "", depth: int = 0) -> list[tuple[str, str]]:
    if depth > 5:
        return []
    found: list[tuple[str, str]] = []
    if isinstance(node, str):
        if prefix:
            found.append((prefix, node))
        return found
    if isinstance(node, dict):
        for raw_key, val in node.items():
            key = str(raw_key)
            path = f"{prefix}.{key}" if prefix else key
            found.extend(_walk_strings(val, prefix=path, depth=depth + 1))
    elif isinstance(node, list):
        for idx, item in enumerate(node[:8]):
            path = f"{prefix}[{idx}]" if prefix else f"[{idx}]"
            found.extend(_walk_strings(item, prefix=path, depth=depth + 1))
    return found


def _leaf_key(path: str) -> str:
    return path.rsplit(".", 1)[-1].split("[", 1)[0].lower()


def log_qrcode_payload_shape(
    payload: Any,
    *,
    event_name: str = "",
    instance_name: str = "",
    instance_id: str = "",
) -> None:
    """Log seguro: chaves/tipos/tamanhos, nunca o conteúdo do QR/secret."""
    keys: list[str] = []
    if isinstance(payload, dict):
        keys = sorted(str(k) for k in payload.keys())
        data = payload.get("data")
        if isinstance(data, dict):
            keys.append("data." + ",".join(sorted(str(k) for k in data.keys())))
    fields: list[str] = []
    for path, value in _walk_strings(payload):
        leaf = _leaf_key(path)
        if leaf not in _IMAGE_KEYS and leaf not in _TEXT_KEYS and leaf not in {"qrcode", "code"}:
            continue
        fields.append(
            f"{path}:type={type(value).__name__}:len={len(value)}:kind={_kind(value)}"
            f":data_image={str(value).startswith('data:image/')}"
            f":png={str(value).replace(' ', '').startswith(_PNG_B64_MAGIC)}"
        )
    logger.info(
        "[Evolution] QR payload event=%s instance=%s instance_id=%s keys=%s fields=%s",
        event_name or "?",
        instance_name or "?",
        instance_id or "?",
        keys,
        fields or "none",
    )


def normalize_evolution_qr(payload: Any) -> str:
    """
    Converte o payload QRCODE do Evolution-Go em data:image/png;base64,...

    Preferência: PNG real (data.qrcode / base64). Texto de pareamento (data.code,
    2@..., wa.me) vira PNG gerado localmente. Nunca usa URL/texto como src de <img>.
    """
    if isinstance(payload, str):
        payload = {"qrcode": payload}
    if not isinstance(payload, dict):
        return ""

    strings = _walk_strings(payload)
    image_candidates: list[str] = []
    text_candidates: list[str] = []
    for path, value in strings:
        leaf = _leaf_key(path)
        stripped = value.strip()
        if not stripped:
            continue
        if leaf in _IMAGE_KEYS:
            if _looks_like_png(stripped):
                image_candidates.append(stripped)
            elif _looks_like_pairing_text(stripped):
                text_candidates.append(stripped)
        elif leaf in _TEXT_KEYS:
            if _looks_like_pairing_text(stripped):
                text_candidates.append(stripped)
            elif _looks_like_png(stripped):
                image_candidates.append(stripped)

    if not image_candidates and not text_candidates:
        for _path, value in strings:
            stripped = value.strip()
            if _looks_like_png(stripped):
                image_candidates.append(stripped)
            elif _looks_like_pairing_text(stripped):
                text_candidates.append(stripped)

    if image_candidates:
        try:
            return _to_data_uri_from_png_value(image_candidates[0])
        except Exception:
            logger.info("[Evolution] QR PNG candidate rejected kind=%s", _kind(image_candidates[0]))

    if text_candidates:
        try:
            return _pairing_text_to_data_uri(text_candidates[0])
        except Exception:
            logger.info(
                "[Evolution] QR pairing text rejected kind=%s len=%s",
                _kind(text_candidates[0]),
                len(text_candidates[0]),
            )

    return ""


def is_normalized_qr_image(value: str) -> bool:
    return (value or "").startswith("data:image/")
