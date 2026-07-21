from django.apps import apps as django_apps
from django.contrib.auth.management import create_permissions
from django.db import migrations


SELLERS_GROUP_NAME = "Vendedores"

SELLERS_PERMISSION_CODENAMES = (
    ("markets", "add_market"),
    ("markets", "change_market"),
    ("markets", "view_market"),
    ("tenants", "view_tenant"),
)


def create_sellers_group(apps, schema_editor):
    # Garante ContentType + Permission antes de atribuir ao grupo.
    for app_config in django_apps.get_app_configs():
        create_permissions(app_config, verbosity=0)

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    group, _ = Group.objects.get_or_create(name=SELLERS_GROUP_NAME)
    perms = []
    for app_label, codename in SELLERS_PERMISSION_CODENAMES:
        perm = Permission.objects.filter(
            content_type__app_label=app_label,
            codename=codename,
        ).first()
        if perm is None:
            raise RuntimeError(
                f"Permissão {app_label}.{codename} não encontrada ao criar grupo Vendedores.",
            )
        perms.append(perm)
    group.permissions.set(perms)


def remove_sellers_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name=SELLERS_GROUP_NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("markets", "0002_market_custom_price"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("tenants", "0006_lgpd_fields"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(create_sellers_group, remove_sellers_group),
    ]
