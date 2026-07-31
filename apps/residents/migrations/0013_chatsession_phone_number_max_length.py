from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("residents", "0012_searching_unregistered_product_state"),
    ]

    operations = [
        migrations.AlterField(
            model_name="chatsession",
            name="phone_number",
            field=models.CharField(db_index=True, max_length=64),
        ),
    ]
