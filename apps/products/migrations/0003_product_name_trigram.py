from django.db import migrations


# Busca fuzzy de produtos usa pg_trgm quando a extensão já existe no banco.
# CREATE EXTENSION / índice GIN NÃO ficam nesta migration: em PRD o role da app
# não tem permissão, e um CREATE EXTENSION que falha aborta a transaction do migrate.
#
# Para ativar trigram depois (superuser):
#   CREATE EXTENSION IF NOT EXISTS pg_trgm;
#   CREATE INDEX IF NOT EXISTS products_product_name_trgm
#     ON products_product USING gin (name gin_trgm_ops);


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0002_product_search_aliases"),
    ]

    operations = [
        migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop),
    ]
