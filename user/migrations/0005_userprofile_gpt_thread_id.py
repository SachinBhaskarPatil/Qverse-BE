# Generated by Django 4.2.1 on 2024-12-13 11:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0004_alter_user_login_method_alter_user_phone'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='gpt_thread_id',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
    ]
