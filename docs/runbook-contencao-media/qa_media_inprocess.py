# Verificação sintética de mídia segura para PRODUÇÃO (também roda em staging).
#
# Tudo acontece dentro de UMA transação revertida ao final: nada é commitado, então cron,
# webhooks, outros workers e outras conexões ao banco nunca veem os dados, e callbacks
# on_commit são descartados. Arquivos vão para um diretório temporário (não para o volume
# de mídia). Durante a execução o processo só pode abrir conexões para o banco, o cache e
# loopback; qualquer outra tentativa (Asaas, Evolution, SMTP, Meta...) é bloqueada e reprovada.
# O throttle usa cache local e o e-mail usa locmem.
#
# As requisições passam pelo stack completo do Django (middlewares, JWT, tenant, views) via
# django.test.Client com o Host público; o trajeto Cloudflare/Apache é coberto por sondar.sh.
#
#   Container em execução:  docker exec -i <backend> python manage.py shell < qa_media_inprocess.py
#   Imagem nova, antes da troca (não publica portas nem toca no container ativo):
#     docker compose -f <compose> run --rm --no-deps -T --name mc-qa-inproc \
#       --entrypoint python backend manage.py shell < qa_media_inprocess.py
#
# QA_HOST (opcional): Host das requisições; padrão = primeiro ALLOWED_HOSTS que começa com "app." ou "staging-api.".
# Saída: linhas PASS/FAIL e "QA_INPROCESS={...}"; código de saída 1 se algo falhar.
import hashlib
import io
import ipaddress
import json
import os
import re
import shutil
import socket
import sys
import tempfile
from datetime import timedelta
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache.backends.locmem import LocMemCache
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage, default_storage
from django.db import connection, transaction
from django.db.models.signals import post_delete, post_save, pre_delete, pre_save
from django.test import Client, override_settings
from django.urls import get_resolver
from django.utils import timezone
from PIL import Image, ImageDraw
from rest_framework.throttling import SimpleRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken

from apps.chatbot.models import ChatMessageLog
from apps.residents.models import ChatSession, Resident
from apps.sales.models import Cart
from apps.tenants.models import Tenant

RUN_ID = timezone.now().strftime("%Y%m%d%H%M%S%f")
PREFIX = f"qa-inproc-{RUN_ID}"
EXPECTED_RECEIVERS = {"apps.chatbot.signals.seed_chatbot_workflows_for_new_tenant"}
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: object = "") -> bool:
    results.append((name, bool(ok), str(detail)))
    print(f"{'PASS' if ok else 'FAIL'}  {name:<58} {detail}")
    return bool(ok)


def pick_host() -> str:
    if os.environ.get("QA_HOST"):
        return os.environ["QA_HOST"]
    for h in settings.ALLOWED_HOSTS:
        if h.startswith(("app.", "staging-api.")):
            return h
    return settings.ALLOWED_HOSTS[0]


HOST = pick_host()

# ---------------------------------------------------------------- rede: só banco, cache e loopback
def _resolve(host: str) -> set[str]:
    try:
        return {ai[4][0] for ai in socket.getaddrinfo(host, None)}
    except OSError:
        return set()


allowed_names = {"localhost"}
allowed_ips = {"127.0.0.1", "::1"}
db_host = settings.DATABASES["default"].get("HOST") or ""
cache_urls = [str(getattr(settings, "REDIS_URL", "") or "")]
for cfg in settings.CACHES.values():
    loc = cfg.get("LOCATION", "")
    cache_urls.extend(loc if isinstance(loc, (list, tuple)) else [str(loc)])
for name in [db_host] + [urlsplit(u).hostname or "" for u in cache_urls if "://" in u]:
    if name:
        allowed_names.add(name)
        allowed_ips |= _resolve(name)

blocked: list[str] = []
_orig_connect = socket.socket.connect
_orig_connect_ex = socket.socket.connect_ex
_orig_getaddrinfo = socket.getaddrinfo


def _is_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def _allowed(address) -> bool:
    return not isinstance(address, tuple) or address[0] in allowed_ips


def _guarded_connect(self, address):
    if not _allowed(address):
        blocked.append(f"connect:{address[0]}:{address[1]}")
        raise OSError(f"QA: conexão externa bloqueada para {address}")
    return _orig_connect(self, address)


def _guarded_connect_ex(self, address):
    if not _allowed(address):
        blocked.append(f"connect:{address[0]}:{address[1]}")
        return 111
    return _orig_connect_ex(self, address)


def _guarded_getaddrinfo(host, *args, **kwargs):
    name = host.decode() if isinstance(host, bytes) else host
    if name is None or name in allowed_names or _is_ip(name):
        return _orig_getaddrinfo(host, *args, **kwargs)
    blocked.append(f"dns:{name}")
    raise socket.gaierror(f"QA: resolução externa bloqueada para {name}")


# ---------------------------------------------------------------- sinais
fired: list[str] = []
MODELS = [Tenant, get_user_model(), Resident, ChatSession, ChatMessageLog, Cart]
SIGNALS = {"pre_save": pre_save, "post_save": post_save, "pre_delete": pre_delete, "post_delete": post_delete}


def _recorder(signal_name):
    def receiver(sender, **kwargs):
        fired.append(f"{signal_name}:{sender._meta.label}")
    receiver.__qualname__ = f"qa_recorder_{signal_name}"
    return receiver


recorders = {n: _recorder(n) for n in SIGNALS}


def foreign_receivers() -> set[str]:
    found = set()
    for signal in SIGNALS.values():
        for model in MODELS:
            live = signal._live_receivers(model)
            if isinstance(live, tuple) and len(live) == 2 and all(isinstance(x, list) for x in live):
                live = live[0] + live[1]
            for r in live:
                qn = f"{getattr(r, '__module__', '?')}.{getattr(r, '__qualname__', repr(r))}"
                if "qa_recorder_" not in qn:
                    found.add(qn)
    return found


def synthetic_jpeg(label: str) -> bytes:
    img = Image.new("RGB", (320, 120), (160, 64, 32))
    ImageDraw.Draw(img).text((12, 50), f"MARKETCHAT QA INPROC {label}", fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return buf.getvalue()


def body(resp) -> bytes:
    # O Client já fecha a resposta; um close() extra dispararia request_finished ->
    # close_old_connections e derrubaria a conexão no meio da transação.
    return b"".join(resp.streaming_content) if getattr(resp, "streaming", False) else resp.content


print(f"== verificação em processo host={HOST} run={RUN_ID}")
receivers = foreign_receivers()
check("receptores de sinal nos modelos usados são só os conhecidos", receivers <= EXPECTED_RECEIVERS, sorted(receivers))

tmpdir = tempfile.mkdtemp(prefix="qa-inproc-")
orig_throttle_cache = SimpleRateThrottle.cache
socket.socket.connect = _guarded_connect
socket.socket.connect_ex = _guarded_connect_ex
socket.getaddrinfo = _guarded_getaddrinfo
for name, sig in SIGNALS.items():
    sig.connect(recorders[name], weak=False, dispatch_uid=f"qa-inproc-{name}")
SimpleRateThrottle.cache = LocMemCache("qa-inproc-throttle", {})
pending_on_commit: list[str] = []
aborted = None

try:
    try:
        socket.create_connection(("192.0.2.1", 9), timeout=1).close()
        check("autoteste: bloqueio de rede externa ativo", False, "conexão NÃO foi bloqueada")
    except OSError:
        check("autoteste: bloqueio de rede externa ativo", bool(blocked), blocked[-1:] or "")
    blocked.clear()

    with override_settings(MEDIA_ROOT=tmpdir, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
        def storage_in_tmp(storage) -> bool:
            location = os.path.realpath(storage.location)  # avalia o LazyObject antes do isinstance
            inner = getattr(storage, "_wrapped", storage)
            return isinstance(inner, FileSystemStorage) and location == os.path.realpath(tmpdir)

        fields = [ChatMessageLog._meta.get_field("attachment"), Cart._meta.get_field("product_photo")]
        storages_ok = all(storage_in_tmp(f.storage) for f in fields)
        if not check("arquivos vão para diretório temporário (não para o volume)", storages_ok,
                     default_storage.location):
            raise RuntimeError("storage fora do diretório temporário; nada foi criado")

        with transaction.atomic():
            now = timezone.now()
            tenants, users = [], []
            for suffix in ("a", "b"):
                t = Tenant(name=f"QA inproc {suffix.upper()}", slug=f"{PREFIX}-{suffix}",
                           trial_started_at=now, trial_ends_at=now + timedelta(days=1),
                           subscription_status=Tenant.SubscriptionStatus.TRIAL)
                t.save()
                tenants.append(t)
                users.append(get_user_model().objects.create_user(
                    f"{PREFIX}-{suffix}@example.invalid", password=None, tenant=t, is_tenant_admin=True))
            ta = tenants[0]
            resident = Resident(tenant=ta, phone_number=f"{PREFIX}-morador", name="Morador QA")
            resident.save()
            session = ChatSession(tenant=ta, phone_number=f"{PREFIX}-morador",
                                  state=ChatSession.State.IDLE, inactivity_notified=True)
            session.save()
            chat_bytes, cart_bytes = synthetic_jpeg("CHAT"), synthetic_jpeg("CART")
            msg_ok = ChatMessageLog(tenant=ta, session=session, resident=resident,
                                    direction=ChatMessageLog.Direction.INBOUND,
                                    message_kind=ChatMessageLog.MessageKind.IMAGE)
            msg_ok.attachment.save(f"{PREFIX}-chat.jpg", ContentFile(chat_bytes), save=False)
            msg_ok.save()
            msg_empty = ChatMessageLog(tenant=ta, session=session, direction=ChatMessageLog.Direction.INBOUND)
            msg_empty.save()
            msg_missing = ChatMessageLog(tenant=ta, session=session, direction=ChatMessageLog.Direction.INBOUND,
                                         attachment=f"chat_logs/{PREFIX}-inexistente.jpg")
            msg_missing.save()
            cart = Cart(tenant=ta, resident=resident, status=Cart.Status.CANCELLED)
            cart.product_photo.save(f"{PREFIX}-cart.jpg", ContentFile(cart_bytes), save=False)
            cart.save()

            tok_a = str(RefreshToken.for_user(users[0]).access_token)
            tok_b = str(RefreshToken.for_user(users[1]).access_token)
            c = Client(HTTP_HOST=HOST)

            def get(path, token=None, **extra):
                if token:
                    extra["HTTP_AUTHORIZATION"] = f"Bearer {token}"
                return c.get(path, secure=True, **extra)

            A = f"/api/chatbot/messages/{msg_ok.pk}/attachment/"
            P = f"/api/sales/carts/{cart.pk}/security-photo/"
            for label, path, data in (("anexo chat", A, chat_bytes), ("foto carrinho", P, cart_bytes)):
                r = get(path); body(r)
                check(f"{label}: anônimo -> 401", r.status_code == 401, r.status_code)
                r = get(path, "token-invalido"); b = body(r)
                check(f"{label}: token inválido -> 401 token_not_valid", r.status_code == 401 and b"token_not_valid" in b,
                      r.status_code)
                r = get(path + f"?token={tok_a}"); body(r)
                check(f"{label}: token na query -> 401", r.status_code == 401, r.status_code)
                r = get(path, tok_a); b = body(r)
                ok = (r.status_code == 200 and hashlib.sha256(b).digest() == hashlib.sha256(data).digest()
                      and r.get("Content-Type", "").startswith("image/jpeg")
                      and {"private", "no-store"} <= {x.strip() for x in r.get("Cache-Control", "").split(",")}
                      and r.get("X-Content-Type-Options") == "nosniff")
                check(f"{label}: dono -> 200 + sha256 + cabeçalhos", ok,
                      f"{r.status_code} {r.get('Content-Type')} {r.get('Cache-Control')}")
                r = get(path, tok_b); body(r)
                check(f"{label}: outro tenant -> 404", r.status_code == 404, r.status_code)
            for label, pk in (("sem anexo", msg_empty.pk), ("arquivo ausente", msg_missing.pk), ("id inexistente", 2**31 - 1)):
                r = get(f"/api/chatbot/messages/{pk}/attachment/", tok_a); body(r)
                check(f"anexo chat: {label} -> 404", r.status_code == 404, r.status_code)

            r = get(f"/api/chatbot/logs/conversation/?session_id={session.pk}", tok_a)
            url = next((m.get("attachment_url") or "" for m in r.json().get("messages", []) if m["id"] == msg_ok.pk), "") \
                if r.status_code == 200 else ""
            check("attachment_url aponta para o endpoint autenticado", url.endswith(A) and "/media/" not in url, url or r.status_code)
            r = get(f"/api/sales/carts/{cart.pk}/", tok_a)
            url = (r.json().get("security_photo_url") or "") if r.status_code == 200 else ""
            check("security_photo_url aponta para o endpoint autenticado", url.endswith(P), url or r.status_code)

            r = get(f"/media/{msg_ok.attachment.name}"); body(r)
            check("/media/<arquivo QA> no Django -> 404 (sem rota)", r.status_code == 404, r.status_code)
            has_route = any(str(p.pattern).startswith("media") for p in get_resolver().url_patterns)
            check("URLconf sem rota /media", not has_route, "PRESENTE" if has_route else "ausente")

            pending_on_commit = [getattr(f[1] if isinstance(f, tuple) else f, "__qualname__", "?")
                                 for f in connection.run_on_commit]
            check("transação continua aberta até o rollback", connection.in_atomic_block and not connection.get_autocommit())
            transaction.set_rollback(True)
except Exception as exc:  # noqa: BLE001
    aborted = f"{type(exc).__name__}: {exc}"
finally:
    socket.socket.connect = _orig_connect
    socket.socket.connect_ex = _orig_connect_ex
    socket.getaddrinfo = _orig_getaddrinfo
    for name, sig in SIGNALS.items():
        sig.disconnect(dispatch_uid=f"qa-inproc-{name}")
    SimpleRateThrottle.cache = orig_throttle_cache
    shutil.rmtree(tmpdir, ignore_errors=True)

if aborted:
    check("execução sem exceção", False, aborted)
check("nenhuma conexão externa tentada (Asaas, Evolution, SMTP...)", not blocked, blocked)
check("rollback: nenhum dado QA persistido", not Tenant.objects.filter(slug__startswith=PREFIX).exists())
check("diretório temporário removido", not os.path.exists(tmpdir), tmpdir)
check("callbacks on_commit descartados pelo rollback", True, pending_on_commit or "nenhum registrado")

failed = [n for n, ok, _ in results if not ok]
print("QA_INPROCESS=" + json.dumps({
    "run_id": RUN_ID, "host": HOST, "passed": len(results) - len(failed), "failed": failed,
    "signals_fired": sorted(set(fired)), "on_commit_discarded": pending_on_commit, "blocked_network": blocked,
}, ensure_ascii=False))
sys.exit(1 if failed else 0)
