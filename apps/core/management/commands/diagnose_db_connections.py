"""Diagnostica uso de conexões no Postgres (útil quando aparece 'too many clients')."""

from __future__ import annotations

import json
from typing import Any

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Mostra max_connections, uso atual e top consumidores no Postgres."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            help="Saída em JSON (sem PII além de roles/apps).",
        )

    def handle(self, *args, **options):
        with connection.cursor() as cur:
            cur.execute("SHOW max_connections")
            max_connections = int(cur.fetchone()[0])
            cur.execute("SHOW superuser_reserved_connections")
            reserved = int(cur.fetchone()[0])
            cur.execute("SELECT count(*) FROM pg_stat_activity")
            total = int(cur.fetchone()[0])
            cur.execute(
                "SELECT count(*) FROM pg_stat_activity WHERE coalesce(state, '') = 'active'"
            )
            active = int(cur.fetchone()[0])
            cur.execute(
                "SELECT count(*) FROM pg_stat_activity WHERE coalesce(state, '') = 'idle'"
            )
            idle = int(cur.fetchone()[0])
            cur.execute(
                """
                SELECT coalesce(datname, '?'), count(*)
                FROM pg_stat_activity
                GROUP BY 1
                ORDER BY 2 DESC
                """
            )
            by_db = [{"db": row[0], "count": int(row[1])} for row in cur.fetchall()]
            cur.execute(
                """
                SELECT coalesce(usename, '?'),
                       coalesce(application_name, ''),
                       coalesce(datname, '?'),
                       count(*)
                FROM pg_stat_activity
                GROUP BY 1, 2, 3
                ORDER BY 4 DESC
                LIMIT 25
                """
            )
            by_app = [
                {
                    "role": row[0],
                    "app": row[1],
                    "db": row[2],
                    "count": int(row[3]),
                }
                for row in cur.fetchall()
            ]

        available = max_connections - reserved - total
        payload: dict[str, Any] = {
            "max_connections": max_connections,
            "superuser_reserved": reserved,
            "total": total,
            "active": active,
            "idle": idle,
            "available_approx": available,
            "by_db": by_db,
            "by_app_top": by_app,
            "conn_max_age": connection.settings_dict.get("CONN_MAX_AGE"),
            "database": connection.settings_dict.get("NAME"),
        }

        if options["json"]:
            self.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False))
            return

        self.stdout.write(
            f"max_connections={max_connections} reserved={reserved} "
            f"total={total} active={active} idle={idle} available≈{available}"
        )
        self.stdout.write("Por database:")
        for item in by_db:
            self.stdout.write(f"  - {item['db']}: {item['count']}")
        self.stdout.write("Top roles/apps:")
        for item in by_app[:12]:
            app = item["app"] or "(sem application_name)"
            self.stdout.write(
                f"  - {item['role']} @ {item['db']} [{app}]: {item['count']}"
            )
        if available <= 5:
            self.stderr.write(
                self.style.ERROR(
                    "Slots quase esgotados. Suba max_connections ou reduza pools "
                    "de sonar/tracker*/outros apps neste Postgres."
                )
            )
