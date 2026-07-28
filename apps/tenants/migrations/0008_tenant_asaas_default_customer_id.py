from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0007_tenant_is_bot_active_global"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenant",
            name="asaas_default_customer_id",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Customer Asaas Consumidor Final para cobranças PIX avulsas no chat.",
                max_length=64,
            ),
        ),
    ]
