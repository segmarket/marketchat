from django.db import migrations


# Busca fuzzy de condomínio usa pg_trgm quando a extensão já existe no banco.
# CREATE EXTENSION / índice GIN NÃO ficam nesta migration: em PRD o role da app
# não tem permissão, e um CREATE EXTENSION que falha aborta a transaction do migrate.
#
# Para ativar trigram depois (superuser):
#   CREATE EXTENSION IF NOT EXISTS pg_trgm;
#   CREATE INDEX IF NOT EXISTS markets_market_name_trgm
#     ON markets_market USING gin (name gin_trgm_ops);


class Migration(migrations.Migration):

    dependencies = [
        ("markets", "0003_sellers_group"),
    ]

    operations = [
        migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop),
    ]
