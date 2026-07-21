from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chatbot", "0006_add_greeting_intent"),
    ]

    operations = [
        migrations.AlterField(
            model_name="chatmessagelog",
            name="direction",
            field=models.CharField(
                choices=[
                    ("INBOUND", "Morador"),
                    ("OUTBOUND", "Bot"),
                    ("AGENT", "Atendente"),
                ],
                max_length=16,
            ),
        ),
    ]
