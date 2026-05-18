"""Sincroniza perfil e metadados da instância a partir do Evolution GO."""

from __future__ import annotations

import logging
import re
from typing import Any

from apps.integrations.models import WhatsappInstance
from apps.integrations.services.evolution_client import EvolutionClient

logger = logging.getLogger(__name__)


def phone_from_jid(jid: str) -> str:
    if not jid:
        return ""
    local = jid.split("@", 1)[0]
    digits = re.sub(r"\D", "", local.split(":")[0])
    return digits


def platform_from_os_name(os_name: str) -> str:
    value = (os_name or "").strip().lower()
    if not value:
        return WhatsappInstance.Platform.UNKNOWN
    if "android" in value:
        return WhatsappInstance.Platform.ANDROID
    if any(k in value for k in ("ios", "iphone", "ipad", "apple")):
        return WhatsappInstance.Platform.IOS
    return WhatsappInstance.Platform.UNKNOWN


def apply_remote_row_to_instance(
    instance: WhatsappInstance,
    remote: dict[str, Any],
) -> list[str]:
    """Atualiza campos locais a partir da linha do GET /instance/all."""
    updates: list[str] = []
    jid = str(remote.get("jid") or remote.get("Jid") or "")
    phone = phone_from_jid(jid) or (instance.phone_number or "")
    if phone and phone != instance.phone_number:
        instance.phone_number = phone
        updates.append("phone_number")

    profile_name = str(
        remote.get("profileName")
        or remote.get("pushName")
        or remote.get("name")
        or ""
    ).strip()
    if profile_name and profile_name != instance.profile_name:
        instance.profile_name = profile_name
        updates.append("profile_name")

    picture = str(
        remote.get("profilePictureUrl")
        or remote.get("profile_picture_url")
        or remote.get("picture")
        or ""
    ).strip()
    if picture and picture != instance.profile_picture_url:
        instance.profile_picture_url = picture
        updates.append("profile_picture_url")

    os_name = str(remote.get("os_name") or remote.get("osName") or "")
    platform = platform_from_os_name(os_name)
    if platform != instance.platform:
        instance.platform = platform
        updates.append("platform")

    reason = str(remote.get("disconnect_reason") or remote.get("disconnectReason") or "")
    if reason != instance.disconnect_reason:
        instance.disconnect_reason = reason
        updates.append("disconnect_reason")

    connected = remote.get("connected")
    if connected is True:
        if instance.connection_status != WhatsappInstance.ConnectionStatus.OPEN:
            instance.connection_status = WhatsappInstance.ConnectionStatus.OPEN
            updates.append("connection_status")
    elif connected is False and instance.connection_status == WhatsappInstance.ConnectionStatus.OPEN:
        instance.connection_status = WhatsappInstance.ConnectionStatus.CLOSE
        updates.append("connection_status")

    return updates


def resolve_instance_phone(instance: WhatsappInstance) -> str:
    """Número E.164 só dígitos (exibição e fallback)."""
    for raw in (instance.phone_number, instance.pair_phone):
        digits = re.sub(r"\D", "", raw or "")
        if digits:
            return digits
    return ""


def resolve_avatar_target(
    instance: WhatsappInstance,
    remote: dict[str, Any] | None = None,
) -> str:
    """JID ou número normalizado para POST /user/avatar."""
    jid = ""
    if remote:
        jid = str(remote.get("jid") or remote.get("Jid") or "").strip()
    if jid:
        return EvolutionClient.normalize_avatar_target(jid)
    phone = resolve_instance_phone(instance)
    if phone:
        return EvolutionClient.normalize_avatar_target(phone)
    return ""


def sync_profile_avatar_from_evolution(
    instance: WhatsappInstance,
    *,
    client: EvolutionClient | None = None,
    try_both_previews: bool = True,
) -> bool:
    """
    Busca avatar do número conectado via POST /user/avatar e persiste em profile_picture_url.
    Retorna True se o campo foi atualizado.
    """
    if not instance.api_key:
        return False
    if instance.connection_status != WhatsappInstance.ConnectionStatus.OPEN:
        return False

    client = client or EvolutionClient()
    remote = None
    try:
        remote = client.fetch_remote_instance(instance_name=instance.instance_name)
        if remote:
            fields = apply_remote_row_to_instance(instance, remote)
            if fields:
                instance.save(update_fields=[*fields, "updated_at"])
    except Exception:
        pass

    target = resolve_avatar_target(instance, remote)
    if not target:
        return False

    previews = (True, False) if try_both_previews else (True,)
    avatar = ""
    try:
        for preview in previews:
            payload = client.fetch_user_avatar(
                number=target,
                instance_api_key=instance.api_key,
                preview=preview,
            )
            avatar = client.extract_avatar_image(payload)
            if avatar:
                break
    except Exception as exc:
        logger.info(
            "Avatar não obtido para %s (%s): %s",
            instance.instance_name,
            target.split("@", 1)[0][-4:].rjust(8, "*"),
            exc,
        )
        return False

    if not isinstance(avatar, str):
        return False
    avatar = avatar.strip()
    if not avatar or avatar == instance.profile_picture_url:
        return False

    instance.profile_picture_url = avatar
    instance.save(update_fields=["profile_picture_url", "updated_at"])
    return True
