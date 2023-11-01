from django import forms
from .models import Ticket

class CreateTicket(forms.ModelForm):
     class Meta:
        model= Ticket
        fields = ["title", "description", "category"]
        labels={
            "title": "Title",
            "description": "Description",
        }
        error_messages={
            "required":"Yout name must be entered",
            "max_length": "Please enter a shorter name!"
        }   
