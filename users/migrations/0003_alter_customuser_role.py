# Generated by Django 5.1.3 on 2024-12-14 17:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_customuser_checkbox'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='role',
            field=models.CharField(choices=[('User', 'User'), ('Journalist', 'Journalist'), ('Editor', 'Editor'), ('Admin', 'Admin')], default='User', max_length=50),
        ),
    ]
