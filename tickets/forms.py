from django import forms
from .models import Ticket
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "password1", "password2")
        help_texts = {
            'username': "This is the unique identifier for each user",
            'password1': None,
            'password2': None,
        }

    def save(self, commit=True):
        user = super(CustomUserCreationForm, self).save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class CreateTicket(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["title", "category", "description"]
        labels = {
            "title": "Title",
            "description": "Description",
        }
        error_messages = {
            "required": "Yout name must be entered",
            "max_length": "Please enter a shorter name!"
        }


class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["title", "category", "status", "description"]

    def __init__(self, user, *args, **kwargs):
        super(TicketForm, self).__init__(*args, **kwargs)
        self.user = user
        if not self.user.profile.is_agent:
            self.fields.pop('status')


class RatingForm(forms.ModelForm):
    RATING_CHOICES = [(str(i), str(i)) for i in range(1, 6)]

    rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        label='Rating',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Ticket
        fields = ['rating']
