# Generated by Django 4.2.6 on 2023-10-11 03:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0007_remove_postaudio_page_id_postaudio_chat_id"),
    ]

    operations = [
        migrations.AlterField(
            model_name="postaudio",
            name="chat_id",
            field=models.CharField(default="0", max_length=20),
        ),
    ]
