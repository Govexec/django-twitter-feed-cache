# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='FollowAccount',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('screen_name', models.CharField(max_length=30)),
                ('external_user_id', models.BigIntegerField(blank=True)),
                ('profile_image_url', models.CharField(max_length=500, blank=True)),
                ('active', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='Tweet',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('external_tweet_id', models.BigIntegerField()),
                ('text', models.CharField(max_length=2500)),
                ('created_at', models.DateTimeField()),
                ('posted_by_user_id', models.BigIntegerField()),
                ('posted_by_screen_name', models.CharField(max_length=30)),
                ('posted_by_name', models.CharField(max_length=200)),
                ('in_reply_to_screen_name', models.CharField(max_length=30, null=True, blank=True)),
                ('in_reply_to_user_id', models.BigIntegerField(null=True, blank=True)),
                ('in_reply_to_status_id', models.BigIntegerField(null=True, blank=True)),
            ],
        ),
    ]
