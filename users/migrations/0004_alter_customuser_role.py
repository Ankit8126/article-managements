# Generated by Django 5.1.3 on 2024-12-16 08:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_alter_customuser_role'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='role',
            field=models.CharField(choices=[('Journalist', 'Journalist'), ('Editor', 'Editor'), ('Admin', 'Admin')], default='Journalist', max_length=50),
        ),
    ]
