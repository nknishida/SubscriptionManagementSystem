# Generated by Django 5.1.7 on 2025-03-26 04:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SubSync', '0031_user_phone_numbers'),
    ]

    operations = [
        migrations.AlterField(
            model_name='provider',
            name='contact_email',
            field=models.EmailField(max_length=254),
        ),
    ]
