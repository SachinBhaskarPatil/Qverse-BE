# Generated by Django 4.2.1 on 2024-10-02 12:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('generator', '0008_question_parent_option'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='question_number',
            field=models.IntegerField(default=1),
        ),
    ]
