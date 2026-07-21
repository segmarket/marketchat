from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("residents", "0008_chatsession_human_handover"),
    ]

    operations = [
        migrations.AlterField(
            model_name="chatsession",
            name="state",
            field=models.CharField(
                choices=[
                    ("AWAITING_NAME", "Aguardando nome"),
                    ("AWAITING_CONDO", "Aguardando condomínio"),
                    ("IDLE", "Conversa livre / compra"),
                    ("AWAITING_MAIN_MENU", "Menu principal"),
                    ("AWAITING_PRODUCT_SUGGESTION", "Aguardando sugestão de produto"),
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
