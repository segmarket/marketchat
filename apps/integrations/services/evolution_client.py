"""Cliente HTTP para Evolution GO."""

from __future__ import annotations

import json
import logging
import re
import uuid as uuid_module
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Iterable

from django.conf import settings

logger = logging.getLogger(__name__)

_DEFAULT_FOOTER = "MarketChat"


def _normalize_reply_buttons(buttons: list[dict[str, str]]) -> list[dict[str, str]]:
    """Evolution GO exige type/displayText/id; {text,id} gera botões vazios no WhatsApp."""
    normalized: list[dict[str, str]] = []
    for btn in buttons:
        btn_id = str(btn.get("id") or btn.get("buttonId") or "").strip()
        label = str(
            btn.get("displayText")
            or btn.get("display_text")
            or btn.get("text")
            or "",
        ).strip()
        if not btn_id or not label:
            continue
        normalized.append(
            {
                "type": str(btn.get("type") or "reply").lower(),
                "id": btn_id,
                "displayText": label[:24],
            },
        )
    return normalized


def _is_uuid(value: str) -> bool:
    try:
        uuid_module.UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def _normalize_instance_row(inst: dict[str, Any]) -> dict[str, Any]:
    """Unifica campos entre Evolution GO (id/name) e Evolution API (instanceId/instanceName)."""
    return {
        **inst,
        "instanceId": str(inst.get("instanceId") or inst.get("id") or ""),
        "instanceName": str(inst.get("instanceName") or inst.get("name") or ""),
    }


def _parse_fetch_instances_payload(payload: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(payload, list):
        for item in payload:
            if not isinstance(item, dict):
                continue
            inst = item.get("instance")
            rows.append(inst if isinstance(inst, dict) else item)
    elif isinstance(payload, dict):
        for key in ("response", "data", "instances"):
            node = payload.get(key)
            if isinstance(node, list):
                return _parse_fetch_instances_payload(node)
        inst = payload.get("instance")
        if isinstance(inst, dict):
            rows.append(inst)
    return [_normalize_instance_row(r) for r in rows if isinstance(r, dict)]


class EvolutionClient:
    """Cliente para Evolution GO. Não confundir com Evolution API (Node)."""

    DEFAULT_EVENTS = ("MESSAGE", "CONNECTION", "QRCODE")

    def __init__(self, base_url: str | None = None, global_api_key: str | None = None):
        self.base_url = (
            base_url or getattr(settings, "EVOLUTION_API_BASE_URL", "") or ""
        ).rstrip("/")
        self.global_api_key = (
            global_api_key
            if global_api_key is not None
            else getattr(settings, "EVOLUTION_GLOBAL_API_KEY", "") or ""
        )

    @staticmethod
    def format_http_error(exc: urllib.error.HTTPError) -> str:
        preview = (getattr(exc, "_body_preview", b"") or b"")[:300]
        body_hint = preview.decode("utf-8", errors="replace").strip()
        if exc.code == 401:
            return (
                "Evolution recusou a chave administrativa (401). "
                "Defina EVOLUTION_GLOBAL_API_KEY no .env.production com o mesmo valor de "
                "GLOBAL_API_KEY ou AUTHENTICATION_API_KEY do container evolution-go no Portainer."
                + (f" Resposta: {body_hint}" if body_hint else "")
            )
        if exc.code == 403:
            return f"Evolution: acesso negado (403).{f' {body_hint}' if body_hint else ''}"
        return f"HTTP Error {exc.code}: {body_hint or exc.reason}"

    def check_global_api_key(self) -> None:
        """Falha rápido se a chave admin estiver ausente ou rejeitada pelo Evolution."""
        if not (self.global_api_key or "").strip():
            raise RuntimeError(
                "EVOLUTION_GLOBAL_API_KEY não está definida. "
                "Copie GLOBAL_API_KEY (evoapicloud) ou AUTHENTICATION_API_KEY do container evolution-go."
            )
        self._request("GET", "/instance/all", apikey=self.global_api_key, timeout=15)

    def _request(
        self,
        method: str,
        path: str,
        *,
        apikey: str,
        body: dict[str, Any] | None = None,
        timeout: int = 30,
    ) -> dict[str, Any]:
        if not self.base_url:
            raise RuntimeError("EVOLUTION_API_BASE_URL não configurado.")
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers: dict[str, str] = {}
        if apikey:
            headers["apikey"] = apikey
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                if not raw:
                    return {}
                parsed = json.loads(raw)
                return parsed if isinstance(parsed, dict) else {"data": parsed}
        except urllib.error.HTTPError as e:
            body_bytes = b""
            try:
                body_bytes = e.read()
            except Exception:
                pass
            level = logging.WARNING if 400 <= e.code < 500 else logging.ERROR
            logger.log(
                level,
                "Evolution HTTP %s em %s %s: %r",
                e.code,
                method,
                path,
                body_bytes[:500],
            )
            e._body_preview = body_bytes  # type: ignore[attr-defined]
            raise

    @staticmethod
    def build_webhook_url(base_url: str, secret: str | None = None) -> str:
        if not base_url:
            return ""
        if not secret:
            return base_url
        sep = "&" if "?" in base_url else "?"
        return f"{base_url}{sep}secret={urllib.parse.quote(secret)}"

    def create_instance(self, *, name: str, instance_id: str, token: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/instance/create",
            apikey=self.global_api_key,
            body={"name": name, "instanceId": instance_id, "token": token},
        )

    def connect_instance(
        self,
        *,
        instance_api_key: str,
        webhook_url: str,
        events: Iterable[str] | None = None,
        phone: str = "",
        immediate: bool = False,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "webhookUrl": webhook_url,
            "subscribe": list(events) if events else list(self.DEFAULT_EVENTS),
            "websocketEnable": "false",
            "natsEnable": "false",
            "rabbitmqEnable": "false",
            "immediate": immediate,
        }
        if phone:
            body["phone"] = phone
        return self._request(
            "POST",
            "/instance/connect",
            apikey=instance_api_key,
            body=body,
        )

    def logout_instance(self, *, instance_api_key: str) -> dict[str, Any]:
        """Evolution GO: encerra sessão WhatsApp (reseta contador de QR quando esgotado)."""
        try:
            return self._request(
                "DELETE",
                "/instance/logout",
                apikey=instance_api_key,
            )
        except urllib.error.HTTPError as exc:
            if self._http_error_is_not_found(exc):
                return {}
            raise

    def logout_instance_by_name(self, instance_name: str, *, instance_api_key: str) -> dict[str, Any]:
        """Logout pela apikey da instância (nome lógico usado só para logs)."""
        del instance_name
        return self.logout_instance(instance_api_key=instance_api_key)

    def disconnect_remote_session(self, *, instance_api_key: str) -> dict[str, Any]:
        """Evolution GO: desconecta sessão sem apagar o registro da instância."""
        try:
            return self._request(
                "POST",
                "/instance/disconnect",
                apikey=instance_api_key,
                body={},
            )
        except urllib.error.HTTPError as exc:
            if self._http_error_is_not_found(exc):
                return {}
            raise

    @staticmethod
    def _http_error_is_qr_limit(exc: urllib.error.HTTPError) -> bool:
        preview = (getattr(exc, "_body_preview", b"") or b"").lower()
        return b"qr code limit" in preview or b"qrcode limit" in preview

    def reconnect_instance(
        self,
        *,
        instance_api_key: str,
        webhook_url: str,
        events: Iterable[str] | None = None,
        phone: str = "",
        reset_session: bool = False,
    ) -> dict[str, Any]:
        """
        Evolution GO não possui /instance/restart — reconexão via logout (opcional),
        connect e leitura do QR.
        """
        if reset_session:
            try:
                self.logout_instance(instance_api_key=instance_api_key)
            except Exception:
                logger.warning(
                    "Evolution logout antes de reconectar falhou (ignorado)",
                    exc_info=True,
                )
            try:
                self.disconnect_remote_session(instance_api_key=instance_api_key)
            except Exception:
                logger.warning(
                    "Evolution disconnect antes de reconectar falhou (ignorado)",
                    exc_info=True,
                )

        connect_payload = self.connect_instance(
            instance_api_key=instance_api_key,
            webhook_url=webhook_url,
            events=events,
            phone=phone,
        )
        try:
            qrcode_payload = self.fetch_qrcode(instance_api_key=instance_api_key)
        except urllib.error.HTTPError as exc:
            if reset_session or not self._http_error_is_qr_limit(exc):
                raise
            logger.info(
                "Evolution QR limit; tentando logout e novo connect",
            )
            self.logout_instance(instance_api_key=instance_api_key)
            connect_payload = self.connect_instance(
                instance_api_key=instance_api_key,
                webhook_url=webhook_url,
                events=events,
                phone=phone,
            )
            qrcode_payload = self.fetch_qrcode(instance_api_key=instance_api_key)

        return {"connect": connect_payload, "qrcode": qrcode_payload}

    @staticmethod
    def _http_error_is_not_found(exc: urllib.error.HTTPError) -> bool:
        preview = (getattr(exc, "_body_preview", b"") or b"").lower()
        if exc.code == 404:
            return True
        return exc.code in (400, 500) and (
            b"not found" in preview
            or b"does not exist" in preview
            or b"record not found" in preview
        )

    @staticmethod
    def _http_error_is_client_disconnected(exc: urllib.error.HTTPError) -> bool:
        """Sessão WhatsApp desconectada no Evolution (não é instância inexistente)."""
        preview = (getattr(exc, "_body_preview", b"") or b"").lower()
        return exc.code == 400 and (
            b"client disconnected" in preview
            or b"disconnected" in preview
            or b"not connected" in preview
        )

    @staticmethod
    def _http_error_is_already_exists(exc: urllib.error.HTTPError) -> bool:
        preview = (getattr(exc, "_body_preview", b"") or b"").lower()
        return exc.code in (400, 409, 500) and b"already exists" in preview

    def fetch_instances(
        self,
        *,
        instance_name: str = "",
        instance_id: str = "",
    ) -> list[dict[str, Any]]:
        """Lista instâncias remotas (evoapicloud: GET /instance/all)."""
        rows: list[dict[str, Any]] = []
        try:
            payload = self._request("GET", "/instance/all", apikey=self.global_api_key)
            rows = _parse_fetch_instances_payload(payload)
        except urllib.error.HTTPError as exc:
            # Não fazer fallback em indisponibilidade/auth: evita 404 falso no fetchInstances.
            if exc.code not in (404,) and not self._http_error_is_not_found(exc):
                raise
            params: list[tuple[str, str]] = []
            if instance_name:
                params.append(("instanceName", instance_name))
            if instance_id:
                params.append(("instanceId", instance_id))
            path = "/instance/fetchInstances"
            if params:
                path = f"{path}?{urllib.parse.urlencode(params)}"
            try:
                payload = self._request("GET", path, apikey=self.global_api_key)
                rows = _parse_fetch_instances_payload(payload)
            except urllib.error.HTTPError as fallback_exc:
                if self._http_error_is_not_found(fallback_exc):
                    rows = []
                else:
                    raise

        if instance_name:
            rows = [r for r in rows if r.get("instanceName") == instance_name]
        if instance_id:
            rows = [
                r
                for r in rows
                if r.get("instanceId") == instance_id or str(r.get("id") or "") == instance_id
            ]
        return rows

    def resolve_remote_instance_id(
        self,
        *,
        instance_name: str = "",
        instance_id: str = "",
    ) -> str:
        """O DELETE do Evolution GO exige UUID; busca o id real pelo nome quando necessário."""
        if instance_name:
            for inst in self.fetch_instances(instance_name=instance_name):
                remote_id = str(inst.get("instanceId") or inst.get("id") or "")
                remote_name = str(inst.get("instanceName") or inst.get("name") or "")
                if remote_id and (remote_name == instance_name or not remote_name):
                    return remote_id
        if instance_id and _is_uuid(instance_id):
            for inst in self.fetch_instances(instance_id=instance_id):
                remote_id = str(inst.get("instanceId") or inst.get("id") or "")
                if remote_id:
                    return remote_id
            return instance_id
        return ""

    def delete_instance(
        self,
        *,
        instance_id: str = "",
        instance_name: str = "",
    ) -> dict[str, Any]:
        """Remove instância no Evolution (path exige UUID, não o nome lógico)."""
        remote_id = self.resolve_remote_instance_id(
            instance_name=instance_name,
            instance_id=instance_id,
        )
        if not remote_id:
            return {}
        encoded = urllib.parse.quote(remote_id, safe="")
        try:
            return self._request(
                "DELETE",
                f"/instance/delete/{encoded}",
                apikey=self.global_api_key,
            )
        except urllib.error.HTTPError as exc:
            if self._http_error_is_not_found(exc):
                return {}
            raise

    def create_instance_safe(
        self, *, name: str, instance_id: str, token: str
    ) -> dict[str, Any]:
        """Cria instância; se já existir pelo nome, remove (via fetch UUID) e tenta de novo."""
        try:
            return self.create_instance(
                name=name, instance_id=instance_id, token=token
            )
        except urllib.error.HTTPError as exc:
            if not self._http_error_is_already_exists(exc):
                raise
            logger.info(
                "Evolution: instância %s já existe; removendo pelo UUID remoto e recriando.",
                name,
            )
            self.delete_instance(instance_name=name, instance_id=instance_id)
            return self.create_instance(
                name=name, instance_id=instance_id, token=token
            )

    def send_text(
        self,
        *,
        instance_api_key: str,
        number: str,
        text: str,
        delay_ms: int = 0,
    ) -> dict[str, Any]:
        body = {
            "number": number,
            "text": text,
            "delay": delay_ms,
        }
        data = self._request(
            "POST",
            "/send/text",
            apikey=instance_api_key,
            body=body,
        )
        if data is None:
            return {}
        assert isinstance(data, dict)
        return data

    def send_buttons(
        self,
        *,
        instance_api_key: str,
        number: str,
        title: str,
        description: str,
        buttons: list[dict[str, str]],
        footer: str = _DEFAULT_FOOTER,
    ) -> dict[str, Any]:
        reply_buttons = _normalize_reply_buttons(buttons)
        if not reply_buttons:
            raise ValueError("Nenhum botão válido para enviar.")
        body: dict[str, Any] = {
            "number": number,
            "title": title,
            "description": description,
            "footer": footer or _DEFAULT_FOOTER,
            "buttons": reply_buttons,
        }
        data = self._request(
            "POST",
            "/send/button",
            apikey=instance_api_key,
            body=body,
        )
        if data is None:
            return {}
        assert isinstance(data, dict)
        return data

    def send_list(
        self,
        *,
        instance_api_key: str,
        number: str,
        title: str,
        description: str,
        button_text: str,
        sections: list[dict[str, Any]],
        footer: str = _DEFAULT_FOOTER,
    ) -> dict[str, Any]:
        footer_text = footer or _DEFAULT_FOOTER
        body: dict[str, Any] = {
            "number": number,
            "title": title,
            "description": description,
            "buttonText": button_text,
            "footerText": footer_text,
            "sections": sections,
            "values": sections,
        }
        data = self._request(
            "POST",
            "/send/list",
            apikey=instance_api_key,
            body=body,
        )
        if data is None:
            return {}
        assert isinstance(data, dict)
        return data

    def send_carousel(
        self,
        *,
        instance_api_key: str,
        number: str,
        body: str,
        cards: list[dict[str, Any]],
        footer: str = _DEFAULT_FOOTER,
    ) -> dict[str, Any]:
        """Carrossel com botões REPLY (alternativa quando /send/list retorna 405)."""
        payload: dict[str, Any] = {
            "number": number,
            "body": body,
            "footer": footer or _DEFAULT_FOOTER,
            "cards": cards,
        }
        data = self._request(
            "POST",
            "/send/carousel",
            apikey=instance_api_key,
            body=payload,
        )
        if data is None:
            return {}
        assert isinstance(data, dict)
        return data

    def download_media(
        self,
        *,
        instance_api_key: str,
        message: dict[str, Any],
    ) -> dict[str, Any]:
        data = self._request(
            "POST",
            "/message/downloadmedia",
            apikey=instance_api_key,
            body={"message": message},
            timeout=60,
        )
        if data is None:
            return {}
        assert isinstance(data, dict)
        return data

    @staticmethod
    def extract_downloaded_media_bytes(payload: Any) -> bytes:
        """Extrai bytes de mídia de resposta downloadmedia (base64)."""
        import base64

        def normalize_b64(value: str) -> bytes:
            value = value.strip()
            if value.startswith("data:"):
                _, _, value = value.partition(",")
            padding = "=" * (-len(value) % 4)
            return base64.b64decode(value + padding)

        def search(node: Any, depth: int = 0) -> bytes:
            if depth > 6:
                return b""
            if isinstance(node, str) and len(node) > 40:
                try:
                    return normalize_b64(node)
                except Exception:
                    return b""
            if not isinstance(node, dict):
                return b""
            for key in ("base64", "data", "file", "media", "buffer"):
                val = node.get(key)
                if isinstance(val, str) and len(val) > 40:
                    try:
                        return normalize_b64(val)
                    except Exception:
                        pass
            for val in node.values():
                if isinstance(val, (dict, list)):
                    found = search(val, depth + 1) if isinstance(val, dict) else b""
                    if found:
                        return found
                    if isinstance(val, list):
                        for item in val:
                            found = search(item, depth + 1)
                            if found:
                                return found
            return b""

        if isinstance(payload, str):
            try:
                return normalize_b64(payload)
            except Exception:
                return b""
        if isinstance(payload, dict):
            return search(payload.get("data", payload))
        return b""

    def fetch_qrcode(self, *, instance_api_key: str) -> dict[str, Any]:
        try:
            return self._request("GET", "/instance/qr", apikey=instance_api_key)
        except urllib.error.HTTPError as e:
            preview = (getattr(e, "_body_preview", b"") or b"").lower()
            if e.code == 400 and b"already logged in" in preview:
                return {"connected": True, "message": "session already logged in"}
            raise

    def connection_state(self, *, instance_api_key: str) -> dict[str, Any]:
        return self._request("GET", "/instance/status", apikey=instance_api_key)

    def fetch_remote_instance(self, *, instance_name: str) -> dict[str, Any] | None:
        rows = self.fetch_instances(instance_name=instance_name)
        return rows[0] if rows else None

    def check_evolution_health(self, *, timeout: int = 3) -> str:
        try:
            self._request(
                "GET",
                "/instance/all",
                apikey=self.global_api_key,
                timeout=timeout,
            )
            return "ok"
        except Exception:
            return "error"

    @staticmethod
    def normalize_avatar_target(number_or_jid: str) -> str:
        """
        Evolution GO exige JID (ex.: 5514999999999@s.whatsapp.net).
        Número só com dígitos faz o endpoint travar até timeout.
        """
        raw = (number_or_jid or "").strip()
        if not raw:
            return ""
        if "@" in raw:
            local, _, domain = raw.partition("@")
            local = local.split(":")[0]
            return f"{local}@{domain}"
        digits = re.sub(r"\D", "", raw)
        if not digits:
            return ""
        return f"{digits}@s.whatsapp.net"

    def fetch_user_avatar(
        self,
        *,
        number: str,
        instance_api_key: str,
        preview: bool = True,
        timeout: int = 12,
    ) -> dict[str, Any]:
        target = self.normalize_avatar_target(number)
        if not target:
            raise ValueError("Número/JID inválido para buscar avatar.")
        return self._request(
            "POST",
            "/user/avatar",
            apikey=instance_api_key,
            body={"number": target, "preview": preview},
            timeout=timeout,
        )

    @staticmethod
    def extract_avatar_image(payload: Any) -> str:
        """Extrai URL ou data-URL de avatar a partir da resposta do POST /user/avatar."""

        def normalize_url(value: str) -> str:
            value = value.strip()
            if not value:
                return ""
            if value.startswith(("http://", "https://", "data:")):
                return value
            if value.startswith("/9j/") or value.startswith("iVBOR"):
                return f"data:image/jpeg;base64,{value}" if value.startswith("/9j/") else f"data:image/png;base64,{value}"
            if len(value) > 80 and re.match(r"^[A-Za-z0-9+/=_-]+$", value[:120]):
                return f"data:image/jpeg;base64,{value}"
            return ""

        def search(node: Any, depth: int = 0) -> str:
            if depth > 5:
                return ""
            if isinstance(node, str):
                return normalize_url(node)
            if not isinstance(node, dict):
                return ""
            wanted = {
                "url",
                "avatar",
                "picture",
                "image",
                "base64",
                "profilepictureurl",
                "profilepicture",
                "profile_picture_url",
                "img",
                "avatarurl",
            }
            for raw_key, val in node.items():
                key = str(raw_key).lower().replace("_", "")
                if key in wanted or "picture" in key or "avatar" in key:
                    if isinstance(val, str):
                        out = normalize_url(val)
                        if out:
                            return out
                    elif isinstance(val, dict):
                        out = search(val, depth + 1)
                        if out:
                            return out
            for val in node.values():
                if isinstance(val, dict):
                    out = search(val, depth + 1)
                    if out:
                        return out
                elif isinstance(val, list):
                    for item in val:
                        out = search(item, depth + 1)
                        if out:
                            return out
            return ""

        if isinstance(payload, str):
            return normalize_url(payload)
        if isinstance(payload, dict):
            data = payload.get("data")
            if isinstance(data, dict):
                url = data.get("url") or data.get("URL")
                if isinstance(url, str):
                    out = normalize_url(url)
                    if out:
                        return out
            return search(payload.get("data", payload) if isinstance(payload.get("data"), dict) else payload)
        return ""

    def restart_instance(
        self,
        *,
        instance_api_key: str,
        webhook_url: str,
        events: Iterable[str] | None = None,
        phone: str = "",
        reset_session: bool = False,
    ) -> dict[str, Any]:
        """Alias de reconnect_instance (Evolution GO não tem /instance/restart)."""
        return self.reconnect_instance(
            instance_api_key=instance_api_key,
            webhook_url=webhook_url,
            events=events,
            phone=phone,
            reset_session=reset_session,
        )

    @staticmethod
    def extract_qrcode_image(payload: Any) -> str:
        def normalize(value: str) -> str:
            value = value.strip()
            if not value or len(value) < 80:
                return ""
            if value.startswith("data:"):
                return value
            return f"data:image/png;base64,{value}"

        def search(node: Any, depth: int = 0) -> str:
            if depth > 4 or not isinstance(node, dict):
                return ""
            wanted = {"base64", "qrcode", "qr", "code", "image", "qrcodebase64"}
            for raw_key, val in node.items():
                if str(raw_key).lower() in wanted:
                    if isinstance(val, str):
                        out = normalize(val)
                        if out:
                            return out
                    elif isinstance(val, dict):
                        out = search(val, depth + 1)
                        if out:
                            return out
            for val in node.values():
                if isinstance(val, dict):
                    out = search(val, depth + 1)
                    if out:
                        return out
            return ""

        if isinstance(payload, str):
            return normalize(payload)
        if not isinstance(payload, dict):
            return ""
        if payload.get("connected"):
            return ""
        data = payload.get("data")
        if isinstance(data, str):
            return normalize(data)
        return search(data if isinstance(data, dict) else payload)

    @staticmethod
    def extract_connection_status(payload: Any) -> str:
        """Normaliza estado de conexão para open | connecting | close | unknown."""

        def pick(value: Any) -> str:
            if not isinstance(value, str):
                return ""
            v = value.strip().lower()
            if v in ("open", "connected"):
                return "open"
            if v in ("connecting", "pairing"):
                return "connecting"
            if v in ("close", "closed", "disconnected", "logout"):
                return "close"
            return ""

        def walk(node: Any, depth: int = 0) -> str:
            if depth > 5:
                return ""
            if isinstance(node, str):
                return pick(node)
            if not isinstance(node, dict):
                return ""
            for key in ("state", "status", "connection", "connectionStatus"):
                if key.lower() in {k.lower() for k in node}:
                    actual_key = next(k for k in node if k.lower() == key.lower())
                    found = pick(node[actual_key]) or walk(node[actual_key], depth + 1)
                    if found:
                        return found
            for val in node.values():
                found = walk(val, depth + 1)
                if found:
                    return found
            return ""

        if not isinstance(payload, dict):
            return "unknown"
        data = payload.get("data", payload)
        return walk(data) or "unknown"
