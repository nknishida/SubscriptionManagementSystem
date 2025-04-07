# Generated by Django 5.1.7 on 2025-04-07 04:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SubSync', '0053_remove_customer_customer_type_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='historicalresource',
            name='last_updated_date',
        ),
        migrations.RemoveField(
            model_name='resource',
            name='last_updated_date',
        ),
        migrations.AddField(
            model_name='historicalresource',
            name='last_payement_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='historicalresource',
            name='payment_method',
            field=models.CharField(default='bank', max_length=50),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='resource',
            name='last_payement_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='resource',
            name='payment_method',
            field=models.CharField(default='bank', max_length=50),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='hardware',
            name='status',
            field=models.CharField(choices=[('Active', 'Active'), ('Inactive', 'Inactive'), ('retired', 'Retired')], max_length=50),
        ),
        migrations.AlterField(
            model_name='historicalhardware',
            name='status',
            field=models.CharField(choices=[('Active', 'Active'), ('Inactive', 'Inactive'), ('retired', 'Retired')], max_length=50),
        ),
        migrations.AlterField(
            model_name='historicalsubscription',
            name='payment_status',
            field=models.CharField(choices=[('Paid', 'Paid'), ('pending', 'pending')], max_length=20),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='payment_status',
            field=models.CharField(choices=[('Paid', 'Paid'), ('pending', 'pending')], max_length=20),
        ),
    ]
