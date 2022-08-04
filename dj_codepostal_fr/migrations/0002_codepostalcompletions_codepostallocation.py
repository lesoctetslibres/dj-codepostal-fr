# Generated by Django 3.2.14 on 2022-08-04 09:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dj_codepostal_fr', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CodePostalCompletions',
            fields=[
                ('portion', models.CharField(help_text='3 first digits', max_length=3, primary_key=True, serialize=False)),
                ('endings', models.CharField(help_text='only store last 2 digits', max_length=300)),
            ],
        ),
        migrations.CreateModel(
            name='CodePostalLocation',
            fields=[
                ('code', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='dj_codepostal_fr.codepostal')),
                ('longitude', models.FloatField(null=True)),
                ('latitude', models.FloatField(null=True)),
            ],
        ),
    ]
