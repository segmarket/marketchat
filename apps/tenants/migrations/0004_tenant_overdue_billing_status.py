from django.db import migrations, models


def migrate_paid_overdue_to_overdue(apps, schema_editor):
    Tenant = apps.get_model("tenants", "Tenant")
    Tenant.objects.filter(subscription_status="PAID_OVERDUE").update(
        subscription_status="OVERDUE"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0003_tenant_trial_subscription_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenant",
            name="overdue_since",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="tenant",
            name="subscription_status",
            field=models.CharField(
                choices=[
                    ("TRIAL", "Trial"),
                    ("ACTIVE", "Ativa"),
                    ("OVERDUE", "Em atraso"),
                    ("SUSPENDED", "Suspensa"),
                    ("CANCELED", "Cancelada"),
                ],
                default="TRIAL",
                max_length=16,
            ),
        ),
        migrations.RunPython(migrate_paid_overdue_to_overdue, migrations.RunPython.noop),
    ]
