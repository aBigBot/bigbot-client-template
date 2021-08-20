# Generated by Django 3.0.4 on 2021-05-06 20:23

import contrib.mixin
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='InputPattern',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('string', models.TextField()),
                ('lang_policy', models.IntegerField(choices=[(0, 'Language Independent'), (1, 'Bounded within language')], default=0, null=True)),
            ],
            bases=(contrib.mixin.Model, models.Model),
        ),
        migrations.CreateModel(
            name='ResponsePhrase',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hash', models.CharField(blank=True, default=None, max_length=32, null=True)),
                ('string', models.TextField()),
                ('type', models.CharField(default='big.bot.core.text', max_length=128)),
            ],
            bases=(contrib.mixin.Model, models.Model),
        ),
    ]
