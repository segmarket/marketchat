from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("residents", "0013_chatsession_phone_number_max_length"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatsession",
            name="pending_intent",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Intenção da IA no onboarding (ex.: reclamacao); limpa após o cadastro.",
                max_length=32,
            ),
        ),
    ]
