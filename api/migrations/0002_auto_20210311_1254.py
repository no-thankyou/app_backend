# Generated by Django 3.1.7 on 2021-03-11 09:54

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='event',
            name='photos',
        ),
        migrations.AlterField(
            model_name='eventphoto',
            name='event',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='photos', to='api.event', verbose_name='Событие'),
        ),
    ]
