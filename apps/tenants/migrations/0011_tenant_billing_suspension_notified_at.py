from django.db import migrations, models
from django.db.models import F


def mark_current_suspensions_as_notified(apps, schema_editor):
    # Suspensões anteriores a este campo não recebem o e-mail retroativamente.
    Tenant = apps.get_model("tenants", "Tenant")
    Tenant.objects.filter(
        subscription_status="SUSPENDED",
        billing_blocked_at__isnull=False,
    ).update(billing_suspension_notified_at=F("billing_blocked_at"))


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0010_tenant_whatsapp_logout_retry"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenant",
            name="billing_suspension_notified_at",
            field=models.DateTimeField(
                blank=True,
                help_text="E-mail de suspensão enviado ao admin. Anterior a billing_blocked_at = aviso pendente.",
                null=True,
            ),
        ),
        migrations.RunPython(mark_current_suspensions_as_notified, migrations.RunPython.noop),
    ]
