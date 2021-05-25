# Generated by Django 3.1.7 on 2021-04-27 14:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_auto_20210419_1114'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='participation',
            options={'verbose_name': '', 'verbose_name_plural': 'Участники'},
        ),
        migrations.RemoveField(
            model_name='user',
            name='city',
        ),
        migrations.AddField(
            model_name='user',
            name='city',
            field=models.ManyToManyField(blank=True, to='api.City', verbose_name='Город'),
        ),
    ]
