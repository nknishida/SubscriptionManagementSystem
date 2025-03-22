# Generated by Django 5.1.4 on 2025-03-19 18:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SubSync', '0020_remove_subscription_created_by_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='reminder',
            name='scheduled_task_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='resource',
            name='billing_cycle',
            field=models.CharField(choices=[('monthly', 'Monthly'), ('yearly', 'Yearly')], default='monthly', max_length=20),
        ),
        migrations.AddField(
            model_name='resource',
            name='hosting_location',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='resource',
            name='hosting_type',
            field=models.CharField(choices=[('inhouse', 'In-House'), ('cloud', 'Cloud')], default='inhouse', max_length=20),
        ),
        migrations.AddField(
            model_name='resource',
            name='last_updated_date',
            field=models.DateField(auto_now=True),
        ),
        migrations.AddField(
            model_name='resource',
            name='next_payment_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='resource',
            name='provisioned_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='resource',
            name='resource_cost',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=10),
        ),
        migrations.AddField(
            model_name='resource',
            name='storage_capacity',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='resource',
            name='resource_type',
            field=models.CharField(choices=[('database', 'Database'), ('compute', 'Compute'), ('storage', 'Storage'), ('network', 'Network'), ('website', 'Website'), ('web_and_app_hosting', 'Web and App Hosting')], max_length=50),
        ),
        migrations.AlterField(
            model_name='resource',
            name='status',
            field=models.CharField(choices=[('available', 'Available'), ('in_use', 'In Use'), ('maintenance', 'Maintenance'), ('active', 'Active')], max_length=20),
        ),
        migrations.AlterModelTable(
            name='resource',
            table=None,
        ),
    ]
