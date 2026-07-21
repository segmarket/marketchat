from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("residents", "0007_lgpd_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatsession",
            name="is_bot_active",
            field=models.BooleanField(
                db_index=True,
                default=True,
                help_text="Se False, o chatbot não responde automaticamente (atendimento humano).",
            ),
        ),
        migrations.AddField(
            model_name="chatsession",
            name="last_human_interaction_at",
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                help_text="Horário da última mensagem ou toggle do atendente humano.",
                null=True,
            ),
        ),
    ]
