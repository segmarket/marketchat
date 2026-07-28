"""Parser de tags de ocorrência nas respostas da IA e integração com histórico."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from apps.chatbot.services.chat_history import append_assistant_message
from apps.chatbot.services.chatbot_core import OCCURRENCE_COMMAND_TAGS
from apps.chatbot.services.occurrence_dispatch import dispatch_occurrence_tag

if TYPE_CHECKING:
    from apps.integrations.models import WhatsappInstance
    from apps.residents.models import ChatSession, Resident

logger = logging.getLogger(__name__)

TAG_PATTERN = re.compile(r"^\[([A-Z][A-Z0-9_]*)\]\s*", re.MULTILINE)


def parse_occurrence_tag(raw: str) -> tuple[str | None, str]:
    """
    Extrai tag de comando na primeira linha da resposta da IA.
    Retorna (tag_sem_colchetes ou None, texto_limpo_para_o_morador).
    """
    text = (raw or "").strip()
    if not text:
        return None, ""

    match = TAG_PATTERN.match(text)
    if not match:
        return None, text

    tag = match.group(1)
    clean = TAG_PATTERN.sub("", text, count=1).strip()
    if tag not in OCCURRENCE_COMMAND_TAGS:
        logger.warning("Tag de ocorrência desconhecida ignorada: %s", tag)
        return None, clean or text

    return tag, clean or text


def process_ai_assistant_reply(
    *,
    raw_reply: str,
    session: ChatSession,
    tenant_id: int,
    instance: WhatsappInstance,
    resident: Resident,
    user_message: str,
    owner_pre_notified: bool = False,
    record_assistant: bool = True,
) -> tuple[str, str | None]:
    """
    Interpreta tags, dispara alertas e grava apenas o texto limpo no histórico.
    Retorna (texto_para_whatsapp, tag ou None).
    """
    tag, clean = parse_occurrence_tag(raw_reply)
    body = clean or (raw_reply or "").strip()

    if tag:
        dispatch_occurrence_tag(
            tag=tag,
            tenant_id=tenant_id,
            instance=instance,
            resident=resident,
            session=session,
            user_message=user_message,
            owner_pre_notified=owner_pre_notified,
        )

    if body and record_assistant:
        append_assistant_message(session, body)

    return body, tag
