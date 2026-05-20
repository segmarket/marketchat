from datetime import timedelta

from django.db import migrations, models
from django.utils import timezone


def backfill_trial_started_at(apps, schema_editor):
    Tenant = apps.get_model("tenants", "Tenant")
    for tenant in Tenant.objects.all():
        if not tenant.trial_started_at:
            started = tenant.created_at or (tenant.trial_ends_at - timedelta(days=7))
            tenant.trial_started_at = started
            tenant.save(update_fields=["trial_started_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0002_profile_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenant",
            name="trial_started_at",
            field=models.DateTimeField(default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="tenant",
            name="subscription_status",
            field=models.CharField(
                choices=[
                    ("TRIAL", "Trial"),
                    ("ACTIVE", "Active"),
                    ("PAID_OVERDUE", "Paid overdue"),
                    ("CANCELED", "Canceled"),
                ],
                default="TRIAL",
                max_length=16,
            ),
        ),
        migrations.RunPython(backfill_trial_started_at, migrations.RunPython.noop),
    ]
