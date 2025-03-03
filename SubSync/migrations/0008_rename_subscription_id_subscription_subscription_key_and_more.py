# Generated by Django 5.1.4 on 2025-03-01 07:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SubSync', '0007_hardware_hardwareservice_purchase_warranty'),
    ]

    operations = [
        migrations.RenameField(
            model_name='subscription',
            old_name='subscription_id',
            new_name='subscription_key',
        ),
        migrations.RemoveField(
            model_name='utilities',
            name='billing_type',
        ),
        migrations.AddField(
            model_name='utilities',
            name='utility_name',
            field=models.CharField(default='electricity', max_length=255),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='utilities',
            name='utility_type',
            field=models.CharField(choices=[('Prepaid', 'Prepaid'), ('Postpaid', 'Postpaid')], max_length=50),
        ),
    ]
