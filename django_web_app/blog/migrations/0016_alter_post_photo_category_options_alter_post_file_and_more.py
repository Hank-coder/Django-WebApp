# Generated by Django 4.2.6 on 2023-11-08 16:36

import blog.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0015_alter_post_photo_category_options_and_more"),
    ]

    operations = [
        migrations.DeleteModel(
            name="GPTImage",
        ),
    ]
