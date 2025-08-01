# Generated by Django 4.2.1 on 2024-10-23 11:39

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('generator', '0012_universe_meta_universe_narrator_voice_description_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='QuestRewardCollection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField()),
                ('image_path', models.CharField(max_length=255)),
                ('quest', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='generator.quest')),
            ],
        ),
    ]
