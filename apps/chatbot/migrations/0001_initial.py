import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ChatbotWorkflow",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(default="Fluxo principal", max_length=255)),
                ("is_active", models.BooleanField(default=True)),
                ("flow_data", models.JSONField(blank=True, default=dict)),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)ss",
                        to="tenants.tenant",
                    ),
                ),
            ],
            options={
                "ordering": ["-updated_at"],
                "indexes": [
                    models.Index(
                        fields=["tenant", "is_active"],
                        name="chatbot_cha_tenant__a8e2c1_idx",
                    ),
                ],
            },
        ),
    ]
