# SOMENTE STAGING. Cria dados sintéticos COMMITADOS para validar a entrega autenticada
# de mídia por HTTP (Cloudflare -> Apache -> Docker) e na interface, sem fotos de clientes.
#
#   docker exec -i -e QA_RUN_ID=<id> -e QA_CONFIRM_STAGING=1 <container> python manage.py shell < qa_media_seed.py
#
# Em produção NÃO use: o agendamento dos comandos periódicos (cron) não está versionado e
# provision_tenant_default_asaas_customers, cleanup_expired_carts e send_inactivity_followups
# selecionam tenants/carrinhos/sessões por estado. Para produção use qa_media_inprocess.py.
#
# Mitigações mesmo em staging: sem Market (fora do provisionamento Asaas), carrinho CANCELLED
# (fora de cleanup/sync de Pix), sessão com inactivity_notified=True e sem WhatsappInstance
# (fora do follow-up), trial válido por 1 dia (fora de check_subscriptions).
# Imprime uma linha "QA_JSON={...}"; remova com qa_media_cleanup.py.
import hashlib
import io
import json
import os
import re
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from PIL import Image, ImageDraw
from rest_framework_simplejwt.tokens import RefreshToken

from apps.chatbot.models import ChatMessageLog
from apps.residents.models import ChatSession, Resident
from apps.sales.models import Cart
from apps.tenants.models import Tenant

PRODUCTION_HOSTS = {"app.marketchat.com.br", "api.marketchat.com.br", "marketchat.com.br"}
if os.environ.get("QA_CONFIRM_STAGING") != "1":
    raise SystemExit("Recusado: defina QA_CONFIRM_STAGING=1 (este seed é só para staging).")
if PRODUCTION_HOSTS & {h.lower() for h in settings.ALLOWED_HOSTS}:
    raise SystemExit("Recusado: ALLOWED_HOSTS contém hostname de produção.")
if "sandbox" not in (getattr(settings, "ASAAS_API_URL", "") or ""):
    raise SystemExit("Recusado: ASAAS_API_URL não é sandbox.")

RUN_ID = os.environ.get("QA_RUN_ID") or timezone.now().strftime("%Y%m%d%H%M%S")
if not re.fullmatch(r"[0-9a-z]{6,32}", RUN_ID):
    raise SystemExit("QA_RUN_ID deve ter 6-32 caracteres [0-9a-z].")

PREFIX = f"qa-media-{RUN_ID}"
if Tenant.objects.filter(slug__startswith=PREFIX).exists():
    raise SystemExit(f"Já existem tenants {PREFIX}-*; use outro QA_RUN_ID ou rode o cleanup.")


def synthetic_jpeg(label: str) -> bytes:
    img = Image.new("RGB", (320, 120), (32, 96, 160))
    ImageDraw.Draw(img).text((12, 50), f"MARKETCHAT QA {label} {RUN_ID}", fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return buf.getvalue()


def make_tenant(suffix: str, with_password: bool):
    now = timezone.now()
    tenant = Tenant(
        name=f"QA mídia {RUN_ID} {suffix.upper()} (apagar)",
        slug=f"{PREFIX}-{suffix}",
        trial_started_at=now,
        trial_ends_at=now + timedelta(days=1),
        subscription_status=Tenant.SubscriptionStatus.TRIAL,
    )
    tenant.save()
    password = secrets.token_urlsafe(18) if with_password else None
    user = get_user_model().objects.create_user(
        f"{PREFIX}-{suffix}@example.com",
        password=password,
        tenant=tenant,
        is_tenant_admin=True,
    )
    return tenant, user, password


def save(obj):
    obj.save()
    return obj


with transaction.atomic():
    tenant_a, user_a, password_a = make_tenant("a", with_password=True)
    tenant_b, user_b, _ = make_tenant("b", with_password=False)

    resident = save(Resident(tenant=tenant_a, phone_number=f"{PREFIX}-morador", name=f"Morador QA {RUN_ID}"))
    session = save(ChatSession(tenant=tenant_a, phone_number=f"{PREFIX}-morador",
                               state=ChatSession.State.IDLE, inactivity_notified=True))

    chat_bytes = synthetic_jpeg("CHAT")
    msg_ok = ChatMessageLog(tenant=tenant_a, session=session, resident=resident,
                            direction=ChatMessageLog.Direction.INBOUND,
                            message_kind=ChatMessageLog.MessageKind.IMAGE,
                            message_text="[QA] imagem sintética")
    msg_ok.attachment.save(f"{PREFIX}-chat.jpg", ContentFile(chat_bytes), save=False)
    msg_ok.save()

    msg_empty = save(ChatMessageLog(tenant=tenant_a, session=session, resident=resident,
                                    direction=ChatMessageLog.Direction.INBOUND,
                                    message_text="[QA] sem anexo"))
    msg_missing = save(ChatMessageLog(tenant=tenant_a, session=session, resident=resident,
                                      direction=ChatMessageLog.Direction.INBOUND,
                                      message_kind=ChatMessageLog.MessageKind.IMAGE,
                                      message_text="[QA] anexo ausente no storage",
                                      attachment=f"chat_logs/{PREFIX}-inexistente.jpg"))

    cart_bytes = synthetic_jpeg("CART")
    cart = Cart(tenant=tenant_a, resident=resident, status=Cart.Status.CANCELLED)
    cart.product_photo.save(f"{PREFIX}-cart.jpg", ContentFile(cart_bytes), save=False)
    cart.save()

max_msg = ChatMessageLog.all_objects.aggregate(m=Max("pk"))["m"] or 0

print("QA_JSON=" + json.dumps({
    "run_id": RUN_ID,
    "tenant_a": tenant_a.pk,
    "tenant_b": tenant_b.pk,
    "user_a_email": user_a.email,
    "user_a_password": password_a,
    "token_a": str(RefreshToken.for_user(user_a).access_token),
    "token_b": str(RefreshToken.for_user(user_b).access_token),
    "session_id": session.pk,
    "msg_ok": msg_ok.pk,
    "msg_empty": msg_empty.pk,
    "msg_missing": msg_missing.pk,
    "msg_nonexistent": max_msg + 1_000_000,
    "cart_ok": cart.pk,
    "chat_path": msg_ok.attachment.name,
    "cart_path": cart.product_photo.name,
    "chat_sha256": hashlib.sha256(chat_bytes).hexdigest(),
    "cart_sha256": hashlib.sha256(cart_bytes).hexdigest(),
}))
