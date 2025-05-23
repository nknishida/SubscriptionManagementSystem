# Generated by Django 5.1.7 on 2025-04-06 14:56

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SubSync', '0051_remove_resource_customer_customer_resource_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='provider',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='provider',
            name='deleted_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='deleted_provider', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='provider',
            name='is_deleted',
            field=models.BooleanField(default=False),
        ),
    ]
