#!/usr/bin/env python3
"""Extrai de logs de acesso do Apache (texto ou .gz) as requisições a /media.

Somente leitura: não abre arquivos de mídia, só lê os logs informados.
Aceita LogFormat common, combined e vhost_combined; campos extras entre aspas
no fim da linha (ex.: CF-Connecting-IP) vão para a coluna "extra".

    sudo python3 analisar-logs-media.py --since 2026-05-17 /var/log/apache2/*access*.log* \
        > media-hits.csv 2> media-resumo.txt
"""
import argparse
import csv
import gzip
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote, urlsplit

LINE = re.compile(
    r'^(?:(?P<vhost>\S+) )?(?P<ip>\S+) \S+ \S+ \[(?P<ts>[^\]]+)\] '
    r'"(?P<method>[A-Z]+) (?P<target>\S+)(?: [^"]*)?" (?P<status>\d{3}) (?P<bytes>\S+)'
    r'(?: "(?P<ref>[^"]*)" "(?P<ua>[^"]*)")?(?P<extra>.*)$'
)


def normalize(target: str) -> str:
    out: list[str] = []
    for seg in unquote(urlsplit(target).path).split("/"):
        if seg == "..":
            if out:
                out.pop()
        elif seg not in ("", "."):
            out.append(seg)
    return "/" + "/".join(out)


def is_media(path: str) -> bool:
    return path == "/media" or path.startswith("/media/")


def open_log(name: str):
    return gzip.open(name, "rt", errors="replace") if name.endswith(".gz") else open(name, errors="replace")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", required=True, help="AAAA-MM-DD, a partir de 00:00 de Brasília (UTC-3)")
    ap.add_argument("files", nargs="+")
    args = ap.parse_args()
    since = datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=timezone(timedelta(hours=-3)))

    out = csv.writer(sys.stdout)
    out.writerow(["ts", "vhost", "client_ip", "method", "status", "bytes", "path", "raw_target", "user_agent", "extra", "file"])
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    unparsed = 0
    by_status: Counter[str] = Counter()
    served_paths: Counter[str] = Counter()
    served_ips: Counter[str] = Counter()

    for name in args.files:
        with open_log(name) as fh:
            for line in fh:
                m = LINE.match(line.rstrip("\n"))
                if not m:
                    unparsed += 1
                    continue
                try:
                    ts = datetime.strptime(m["ts"], "%d/%b/%Y:%H:%M:%S %z")
                except ValueError:
                    unparsed += 1
                    continue
                first_seen = ts if first_seen is None or ts < first_seen else first_seen
                last_seen = ts if last_seen is None or ts > last_seen else last_seen
                if ts < since:
                    continue
                path = normalize(m["target"])
                if not is_media(path):
                    continue
                status = m["status"]
                by_status[status] += 1
                if status in ("200", "206", "304"):
                    served_paths[path] += 1
                    served_ips[m["ip"]] += 1
                out.writerow([ts.isoformat(), m["vhost"] or "", m["ip"], m["method"], status, m["bytes"],
                              path, m["target"], m["ua"] or "", (m["extra"] or "").strip(), name])

    err = sys.stderr
    print(f"Cobertura dos logs lidos: {first_seen} -> {last_seen}", file=err)
    if first_seen is None or first_seen > since:
        print(f"LACUNA: não há registros anteriores a {first_seen}; período desde {args.since} incompleto.", file=err)
    print(f"Linhas não reconhecidas (LogFormat diferente?): {unparsed}", file=err)
    print(f"Requisições a /media por status: {dict(sorted(by_status.items()))}", file=err)
    print(f"Arquivos distintos entregues (200/206/304): {len(served_paths)}", file=err)
    print("Top IPs com entrega (se forem IPs do Cloudflare, o Apache não registra o cliente real):", file=err)
    for ip, n in served_ips.most_common(20):
        print(f"  {n:6d}  {ip}", file=err)
    return 0


if __name__ == "__main__":
    sys.exit(main())
