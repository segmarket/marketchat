from django.db import migrations, models


def backfill_whatsapp_connected(apps, schema_editor):
    Tenant = apps.get_model("tenants", "Tenant")
    WhatsappInstance = apps.get_model("integrations", "WhatsappInstance")
    open_tenant_ids = (
        WhatsappInstance.objects.filter(
            is_active=True,
            connection_status="open",
        )
        .values_list("tenant_id", flat=True)
        .distinct()
    )
    Tenant.objects.filter(pk__in=open_tenant_ids).update(is_whatsapp_connected=True)


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0008_tenant_asaas_default_customer_id"),
        ("integrations", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenant",
            name="is_whatsapp_connected",
            field=models.BooleanField(
                default=False,
                help_text="Espelho da sessão WhatsApp ativa (Evolution). False = bot offline para clientes.",
            ),
        ),
        migrations.RunPython(backfill_whatsapp_connected, migrations.RunPython.noop),
    ]
