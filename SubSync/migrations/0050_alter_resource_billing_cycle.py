# Generated by Django 5.1.7 on 2025-04-05 06:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SubSync', '0049_alter_resource_billing_cycle'),
    ]

    operations = [
        migrations.AlterField(
            model_name='resource',
            name='billing_cycle',
            field=models.CharField(choices=[('monthly', 'monthly'), ('quarterly', 'quarterly'), ('annual', 'annual')], default='monthly', max_length=20),
        ),
    ]
