from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.mail import send_mail


# Create your models here.

class Expertise(models.TextChoices):
    TECH = 'technical'
    BUSINESS = 'business'
    FINANCIAL = 'financial'


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_agent = models.BooleanField(default=False)
    expertise = models.CharField(max_length=20, choices=Expertise.choices)

    def __str__(self):
        return f"{self.user.username},{self.user.first_name}, {self.user.last_name}"

    class Meta:
        verbose_name_plural = "Profiles"


class Status(models.TextChoices):
    OPEN = 'open'
    CLOSED = 'closed'
    IN_DEVELOPMENT = 'in development'


class Ticket(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    category = models.CharField(max_length=20, choices=Expertise.choices)
    reporter = models.ForeignKey(User, on_delete=models.PROTECT, related_name='reported_tickets')
    assignee = models.ForeignKey(User, on_delete=models.PROTECT, related_name='assigned_tickets', null=True, blank=True)
    time_created = models.DateTimeField(auto_now_add=True)
    time_in_development = models.DateTimeField(null=True, blank=True)
    time_closed = models.DateTimeField(null=True, blank=True)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)

    def __str__(self):
        return f"{self.title}, {self.status}"

    def save(self, *args, **kwargs):
        if self.status == Status.IN_DEVELOPMENT.value and self.time_in_development is None:
            self.time_in_development = timezone.now()
        elif self.status == Status.CLOSED.value and self.time_closed is None:
            self.time_closed = timezone.now()

            self.send_closed_ticket_email()

        super(Ticket, self).save(*args, **kwargs)

    def send_closed_ticket_email(self):
        subject = 'Your ticket has been closed'
        message = f"Your ticket '{self.title}' has been closed. Thank you for using our ticketing system!"
        to_email = [self.reporter.email]

        send_mail(subject, message, from_email, to_email)

    class Meta:
        verbose_name_plural = "Tickets"
