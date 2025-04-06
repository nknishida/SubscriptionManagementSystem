# Generated by Django 5.1.7 on 2025-04-06 07:07

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SubSync', '0050_alter_resource_billing_cycle'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='resource',
            name='customer',
        ),
        migrations.AddField(
            model_name='customer',
            name='resource',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='customer_resources', to='SubSync.resource'),
        ),
        migrations.AlterField(
            model_name='resource',
            name='billing_cycle',
            field=models.CharField(default='monthly', max_length=20),
        ),
    ]
