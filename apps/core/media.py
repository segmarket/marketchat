from __future__ import annotations

import mimetypes
import os

from django.core.exceptions import SuspiciousFileOperation
from django.db.models.fields.files import FieldFile
from django.http import FileResponse, Http404

INLINE_IMAGE_TYPES = frozenset({"image/jpeg", "image/png", "image/webp", "image/gif"})


def protected_file_response(field_file: FieldFile | None) -> FileResponse:
    """Entrega o arquivo de um objeto cuja posse (tenant) a view já validou.

    O caminho vem sempre do campo salvo no banco, nunca da requisição.
    """
    if not field_file or not field_file.name:
        raise Http404
    try:
        handle = field_file.storage.open(field_file.name, "rb")
    except (FileNotFoundError, SuspiciousFileOperation, OSError):
        raise Http404 from None

    content_type, _ = mimetypes.guess_type(field_file.name)
    inline = content_type in INLINE_IMAGE_TYPES
    response = FileResponse(
        handle,
        content_type=content_type if inline else "application/octet-stream",
        as_attachment=not inline,
        filename=os.path.basename(field_file.name),
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    response["Content-Security-Policy"] = "default-src 'none'; sandbox"
    return response
