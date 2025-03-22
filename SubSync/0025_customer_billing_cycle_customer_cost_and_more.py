# Generated by Django 5.1.4 on 2025-03-20 08:17

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SubSync', '0024_remove_resource_hosting_location_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='billing_cycle',
            field=models.CharField(default='monthly', max_length=20),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='customer',
            name='cost',
            field=models.DecimalField(decimal_places=2, default=234, max_digits=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='customer',
            name='end_date',
            field=models.DateField(default='2025-03-19'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='customer',
            name='last_payment_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='customer',
            name='payment_method',
            field=models.CharField(default='Bank_Transfer', max_length=20),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='customer',
            name='start_date',
            field=models.DateField(default='2025-03-19'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='resource',
            name='customer',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='resources', to='SubSync.customer'),
            preserve_default=False,
        ),
        migrations.DeleteModel(
            name='CustomerResource',
        ),
    ]
