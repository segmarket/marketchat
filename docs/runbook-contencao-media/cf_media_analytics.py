#!/usr/bin/env python3
"""Exporta do Cloudflare (GraphQL Analytics) as requisições a /media desde uma data.

Somente leitura. Requer CF_API_TOKEN (Analytics:Read) e CF_ZONE_ID no ambiente.
A janela consultável depende do plano: o script lê settings.notOlderThan e avisa
quando o período pedido começa antes do que o Cloudflare ainda guarda.

    python3 cf_media_analytics.py --since 2026-05-17 > cf-media.csv 2> cf-media-resumo.txt
    python3 cf_media_analytics.py --since 2026-05-17 --no-ip   # se clientIP não estiver disponível
"""
import argparse
import csv
import json
import os
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone

API = "https://api.cloudflare.com/client/v4/graphql"

SETTINGS = """query($zone: string!) { viewer { zones(filter: {zoneTag: $zone}) { settings {
  httpRequestsAdaptiveGroups { enabled maxDuration maxNumberOfFields maxPageSize notOlderThan }
} } } }"""

QUERY = """query($zone: string!, $start: Time!, $end: Time!, $limit: uint64!) {
  viewer { zones(filter: {zoneTag: $zone}) {
    httpRequestsAdaptiveGroups(limit: $limit, orderBy: [count_DESC], filter: {
      datetime_geq: $start, datetime_lt: $end, requestSource: "eyeball",
      OR: [{clientRequestPath_like: "/media%"}, {clientRequestPath_like: "//media%"}]
    }) {
      count
      dimensions { date clientRequestHTTPHost clientRequestPath edgeResponseStatus cacheStatus %IP% }
    }
  } }
}"""


def gql(query: str, variables: dict) -> dict:
    req = urllib.request.Request(
        API,
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"Bearer {os.environ['CF_API_TOKEN']}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.load(resp)
    if body.get("errors"):
        raise SystemExit(f"Erro GraphQL: {json.dumps(body['errors'], ensure_ascii=False)}")
    return body["data"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", required=True, help="AAAA-MM-DD (00:00 de Brasília)")
    ap.add_argument("--no-ip", action="store_true", help="não pede clientIP")
    args = ap.parse_args()
    zone = os.environ["CF_ZONE_ID"]
    err = sys.stderr

    s = gql(SETTINGS, {"zone": zone})["viewer"]["zones"][0]["settings"]["httpRequestsAdaptiveGroups"]
    print(f"Limites do plano: {s}", file=err)
    if not s or not s.get("enabled"):
        raise SystemExit("httpRequestsAdaptiveGroups indisponível para esta zona/token.")

    now = datetime.now(timezone.utc).replace(microsecond=0)
    wanted = datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=timezone(timedelta(hours=-3)))
    oldest = now - timedelta(seconds=int(s["notOlderThan"])) + timedelta(minutes=5)
    start = max(wanted, oldest)
    if start > wanted:
        print(f"LACUNA: o Cloudflare só retém dados a partir de {oldest.isoformat()}; "
              f"período desde {args.since} não está disponível por esta API.", file=err)
    step = timedelta(seconds=min(int(s["maxDuration"]), 86400))
    limit = int(s["maxPageSize"])
    query = QUERY.replace("%IP%", "" if args.no_ip else "clientIP")

    out = csv.writer(sys.stdout)
    out.writerow(["date", "host", "path", "status", "cache_status", "client_ip", "count"])
    by_cache: Counter[str] = Counter()
    by_status: Counter[int] = Counter()
    served: set[tuple[str, str]] = set()
    t = start
    while t < now:
        end = min(t + step, now)
        rows = gql(query, {"zone": zone, "start": t.isoformat(), "end": end.isoformat(), "limit": limit})
        groups = rows["viewer"]["zones"][0]["httpRequestsAdaptiveGroups"]
        if len(groups) >= limit:
            print(f"AVISO: janela {t.isoformat()} atingiu o limite de {limit} linhas; resultado truncado.", file=err)
        for g in groups:
            d = g["dimensions"]
            out.writerow([d["date"], d["clientRequestHTTPHost"], d["clientRequestPath"], d["edgeResponseStatus"],
                          d["cacheStatus"], d.get("clientIP", ""), g["count"]])
            by_cache[d["cacheStatus"]] += g["count"]
            by_status[d["edgeResponseStatus"]] += g["count"]
            if d["edgeResponseStatus"] in (200, 206, 304):
                served.add((d["clientRequestHTTPHost"], d["clientRequestPath"]))
        t = end

    print(f"Período consultado: {start.isoformat()} -> {now.isoformat()} (contagens amostradas pelo Cloudflare)", file=err)
    print(f"Por status: {dict(sorted(by_status.items()))}", file=err)
    print(f"Por cacheStatus: {dict(by_cache)}  (hit/stale/revalidated = havia cópia no cache)", file=err)
    print(f"host+caminho distintos entregues: {len(served)}", file=err)
    return 0


if __name__ == "__main__":
    sys.exit(main())
