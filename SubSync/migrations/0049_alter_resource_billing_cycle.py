# Generated by Django 5.1.7 on 2025-04-05 05:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SubSync', '0048_alter_resource_billing_cycle_alter_warranty_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='resource',
            name='billing_cycle',
            field=models.CharField(choices=[('monthly', 'Monthly'), ('quarterly', 'Quarterly'), ('annual', 'annual')], default='monthly', max_length=20),
        ),
    ]
