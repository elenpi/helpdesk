from django.db.models.query import QuerySet
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin

from django.views import View
from django.views.generic import ListView, DetailView
from django.views.generic.edit import FormView,CreateView

from .forms import CreateTicket, CustomUserCreationForm
from .models import Ticket


# Create your views here.

class Registration(FormView):
    template_name = "registration/register.html"
    form_class = CustomUserCreationForm
    success_url = "/login"

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)

class OpenTicketsList(LoginRequiredMixin, ListView):
    template_name = "tickets/index.html"
    model = Ticket
    context_object_name= "tickets"

    def get_queryset(self):
        user = self.request.user

        if user.profile.is_agent:
            return Ticket.objects.filter(assignee=user)
        return Ticket.objects.filter(reporter=user)


class CreateTicketView(LoginRequiredMixin, CreateView):
    model = Ticket
    form_class = CreateTicket
    template_name = "tickets/ticket_creation.html"
    success_url = "/"

    def form_valid(self, form):
        form.instance.reporter = self.request.user 
        return super().form_valid(form)

class TicketList(LoginRequiredMixin, ListView):
    template_name = "tickets/tickets.html"
    model = Ticket
    context_object_name= "tickets"


class TicketDetail(LoginRequiredMixin, DetailView):
    template_name = "tickets/ticket_detail.html" 
    model = Ticket
