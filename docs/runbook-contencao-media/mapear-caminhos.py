# Mapeia caminhos de /media (vindos dos logs) para tenant/objeto, sem abrir arquivos.
# Executar DENTRO do container, com a lista em /tmp/media-paths.txt (um caminho por linha,
# com ou sem o prefixo /media/):
#
#   docker cp media-paths.txt <container>:/tmp/media-paths.txt
#   docker exec -i <container> python manage.py shell < mapear-caminhos.py > impacto.csv
#   docker exec <container> rm -f /tmp/media-paths.txt
import csv
import sys

from apps.chatbot.models import ChatMessageLog
from apps.sales.models import Cart

names = set()
with open("/tmp/media-paths.txt") as fh:
    for line in fh:
        p = line.strip()
        if p:
            names.add(p.removeprefix("/media/").lstrip("/"))

out = csv.writer(sys.stdout)
out.writerow(["path", "modelo", "objeto_id", "tenant_id", "tenant", "resident_id", "criado_em"])
found = set()
for log in ChatMessageLog.all_objects.filter(attachment__in=names).select_related("tenant"):
    found.add(log.attachment.name)
    out.writerow([log.attachment.name, "ChatMessageLog", log.pk, log.tenant_id, log.tenant.name,
                  log.resident_id or "", log.created_at.isoformat()])
for cart in Cart.objects.filter(product_photo__in=names).select_related("tenant"):
    found.add(cart.product_photo.name)
    out.writerow([cart.product_photo.name, "Cart", cart.pk, cart.tenant_id, cart.tenant.name,
                  cart.resident_id, cart.created_at.isoformat()])
for missing in sorted(names - found):
    out.writerow([missing, "SEM_REGISTRO", "", "", "", "", ""])
