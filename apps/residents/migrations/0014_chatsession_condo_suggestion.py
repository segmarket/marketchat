from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("residents", "0013_chatsession_phone_number_max_length"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatsession",
            name="context_data",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AlterField(
            model_name="chatsession",
            name="state",
            field=models.CharField(
                choices=[
                    ("AWAITING_NAME", "Aguardando nome"),
                    ("AWAITING_CONDO", "Aguardando condomínio"),
                    (
                        "AWAITING_CONDO_SUGGESTION",
                        "Aguardando escolha de condomínio sugerido",
                    ),
                    ("IDLE", "Conversa livre / compra"),
                    ("AWAITING_MAIN_MENU", "Menu principal"),
                    ("AWAITING_SUPPORT_DETAILS", "Aguardando detalhes do suporte"),
                    (
                        "SEARCHING_UNREGISTERED_PRODUCT",
                        "Buscando produto sem cadastro",
                    ),
                    ("WAITING_FOR_HUMAN", "Aguardando atendimento humano"),
                    (
                        "AWAITING_PRODUCT_SUGGESTION",
                        "Aguardando sugestão de produto",
                    ),
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
