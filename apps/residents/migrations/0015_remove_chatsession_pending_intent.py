"""Remove coluna órfã pending_intent (migration revertida sem reverse no banco)."""

from django.db import migrations


def _drop_pending_intent(apps, schema_editor):
    table = "residents_chatsession"
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        if connection.vendor == "postgresql":
            cursor.execute(
                f"ALTER TABLE {table} DROP COLUMN IF EXISTS pending_intent;"
            )
            return
        if connection.vendor == "sqlite":
            cursor.execute(f"PRAGMA table_info({table})")
            columns = {row[1] for row in cursor.fetchall()}
            if "pending_intent" in columns:
                cursor.execute(f"ALTER TABLE {table} DROP COLUMN pending_intent")


class Migration(migrations.Migration):

    dependencies = [
        ("residents", "0014_chatsession_condo_suggestion"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[],
            database_operations=[
                migrations.RunPython(
                    _drop_pending_intent,
                    migrations.RunPython.noop,
                ),
            ],
        ),
    ]
