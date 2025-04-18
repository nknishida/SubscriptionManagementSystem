# Generated by Django 5.1.7 on 2025-04-11 03:17

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SubSync', '0062_notification_hardware_reminderhardware_reminder_type_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='customer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='SubSync.customer'),
        ),
        migrations.AlterField(
            model_name='reminder',
            name='reminder_type',
            field=models.CharField(choices=[('renewal', 'Renewal'), ('maintenance', 'Maintenance'), ('warranty', 'warranty'), ('over due', 'Over Due'), ('server break down', 'Server Break Down'), ('server_expiry', 'Server Expiry'), ('customer_expiry', 'Customer Expiry')], default='renewal', max_length=50),
        ),
    ]
