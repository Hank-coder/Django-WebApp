# Generated by Django 4.2.6 on 2023-11-24 16:30

import blog.models
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0017_alter_post_photo_category_options_alter_post_file_and_more"),
    ]

    operations = [

        migrations.AlterUniqueTogether(
            name="dailyusage",
            unique_together=set(),
        ),
        migrations.AddField(
            model_name="dailyusage",
            name="last_used_at",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.RemoveField(
            model_name="dailyusage",
            name="date",
        ),
    ]
