# Generated by Django 3.1.7 on 2021-03-22 21:04

import datetime
from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0004_auto_20210322_2052"),
    ]

    operations = [
        migrations.AlterField(
            model_name="post",
            name="publish",
            field=models.DateTimeField(
                default=datetime.datetime(2021, 3, 22, 21, 4, 46, 447179, tzinfo=utc)
            ),
        ),
    ]