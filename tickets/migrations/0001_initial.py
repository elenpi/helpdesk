# Generated by Django 4.2.6 on 2023-10-26 13:48

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Ticket',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('status', models.CharField(choices=[('open', 'Open'), ('closed', 'Closed'), ('in development', 'In Development')], default='open', max_length=20)),
                ('category', models.CharField(choices=[('technical', 'Tech'), ('business', 'Business'), ('financial', 'Financial')], max_length=20)),
                ('time_created', models.DateTimeField(auto_now_add=True)),
                ('time_in_development', models.DateTimeField(blank=True, null=True)),
                ('time_closed', models.DateTimeField(blank=True, null=True)),
                ('rating', models.IntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('assignee', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='assigned_tickets', to=settings.AUTH_USER_MODEL)),
                ('reporter', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='reported_tickets', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_agent', models.BooleanField(default=False)),
                ('expertise', models.CharField(choices=[('technical', 'Tech'), ('business', 'Business'), ('financial', 'Financial')], max_length=20)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
