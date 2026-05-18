from __future__ import annotations

import re


def jid_to_phone(remote_jid: str) -> str:
    """Extrai número em dígitos a partir do JID WhatsApp."""
    raw = (remote_jid or "").strip()
    if not raw:
        return ""
    local = raw.split("@")[0].split(":")[0]
    return re.sub(r"\D", "", local)
