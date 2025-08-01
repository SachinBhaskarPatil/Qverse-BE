# Generated by Django 4.2.1 on 2024-10-21 10:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game_interface', '0002_usercollectible'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserUniverseSuggestion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('universe_description', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'user_universe_suggestion',
            },
        ),
    ]
