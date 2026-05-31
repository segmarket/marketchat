from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0002_asaassubaccount"),
    ]

    operations = [
        migrations.AddField(
            model_name="asaassubaccount",
            name="asaas_account_id",
            field=models.CharField(blank=True, db_index=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="asaassubaccount",
            name="asaas_subaccount_api_key",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="asaassubaccount",
            name="asaas_status_general",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AddField(
            model_name="asaassubaccount",
            name="asaas_status_commercial",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AddField(
            model_name="asaassubaccount",
            name="asaas_status_documentation",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AddField(
            model_name="asaassubaccount",
            name="asaas_status_bank",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AddField(
            model_name="asaassubaccount",
            name="status_message",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="asaassubaccount",
            name="status_synced_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
