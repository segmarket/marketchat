from django.db import migrations, models
import django.db.models.deletion

STATE_RENAME_MAP = {
    "ACTIVE_BOT": "IDLE",
    "AWAITING_PRODUCT_SELECTION": "PRODUCT_SEARCH",
    "AWAITING_QUANTITY": "QUANTITY_SELECTION",
    "AWAITING_LOOP_DECISION": "CART_REVIEW",
}

STATE_RENAME_REVERSE = {v: k for k, v in STATE_RENAME_MAP.items()}


def rename_states_forward(apps, schema_editor):
    ChatSession = apps.get_model("residents", "ChatSession")
    for old, new in STATE_RENAME_MAP.items():
        ChatSession.objects.filter(state=old).update(state=new)


def rename_states_backward(apps, schema_editor):
    ChatSession = apps.get_model("residents", "ChatSession")
    for new, old in STATE_RENAME_REVERSE.items():
        ChatSession.objects.filter(state=new).update(state=old)


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0001_initial"),
        ("residents", "0004_chat_session_inactivity_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatsession",
            name="last_discussed_product",
            field=models.ForeignKey(
                blank=True,
                help_text="Último produto citado em disponibilidade ou busca (memória de curto prazo).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="discussed_in_sessions",
                to="products.product",
            ),
        ),
        migrations.RunPython(rename_states_forward, rename_states_backward),
        migrations.AlterField(
            model_name="chatsession",
            name="state",
            field=models.CharField(
                choices=[
                    ("AWAITING_NAME", "Aguardando nome"),
                    ("AWAITING_CONDO", "Aguardando condomínio"),
                    ("IDLE", "Conversa livre / compra"),
                    ("PRODUCT_SEARCH", "Busca de produto"),
                    ("QUANTITY_SELECTION", "Seleção de quantidade"),
                    ("CART_REVIEW", "Revisão do carrinho"),
                    ("AWAITING_PHOTO", "Aguardando foto"),
                ],
                default="AWAITING_NAME",
                max_length=32,
            ),
        ),
    ]
