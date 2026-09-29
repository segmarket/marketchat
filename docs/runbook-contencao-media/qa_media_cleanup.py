# Remove os dados criados por qa_media_seed.py. Executar DENTRO do container:
#
#   docker exec -i -e QA_RUN_ID=<id> <container> python manage.py shell < qa_media_cleanup.py
#
# Só apaga tenants cujo slug é exatamente qa-media-<id>-a / -b e arquivos cujo
# nome contém qa-media-<id>; qualquer outra coisa aborta sem alterar nada.
import os
import re

from django.db import transaction

from apps.chatbot.models import ChatMessageLog
from apps.sales.models import Cart
from apps.tenants.models import Tenant

RUN_ID = os.environ.get("QA_RUN_ID", "")
if not re.fullmatch(r"[0-9a-z]{6,32}", RUN_ID):
    raise SystemExit("Defina QA_RUN_ID (o mesmo usado no seed).")

PREFIX = f"qa-media-{RUN_ID}"
tenants = list(Tenant.objects.filter(slug__in=[f"{PREFIX}-a", f"{PREFIX}-b"]))
if not tenants:
    raise SystemExit(f"Nenhum tenant {PREFIX}-* encontrado; nada a limpar.")

files = []
for log in ChatMessageLog.all_objects.filter(tenant__in=tenants).exclude(attachment=""):
    files.append(log.attachment)
for cart in Cart.objects.filter(tenant__in=tenants).exclude(product_photo=""):
    files.append(cart.product_photo)

for f in files:
    if PREFIX not in f.name:
        raise SystemExit(f"Arquivo fora do padrão QA, abortando: {f.name}")

removed = []
for f in files:
    if f.storage.exists(f.name):
        f.storage.delete(f.name)
        removed.append(f.name)

with transaction.atomic():
    deleted = [t.slug for t in tenants]
    for t in tenants:
        t.delete()

leftover = Tenant.objects.filter(slug__startswith=PREFIX).count()
print(f"QA_CLEANUP tenants={deleted} arquivos_removidos={removed} restantes={leftover}")
