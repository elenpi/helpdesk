from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin

from django.views import View
from django.views.generic.base import TemplateView
from django.views.generic import ListView, DetailView
from django.views.generic.edit import FormView,CreateView

from .forms import CreateTicket
from .models import Ticket


# Create your views here.

class OpenTicketsList(ListView):
    template_name = "tickets/index.html"
    model = Ticket
    context_object_name= "tickets"

class CreateTicketView(LoginRequiredMixin,CreateView):
    model = Ticket
    form_class = CreateTicket
    template_name = "tickets/ticket_creation.html"
    success_url = "/"

    def form_valid(self, form):
        form.instance.reporter = self.request.user 
        return super().form_valid(form)

class TicketList(ListView):
    template_name = "tickets/tickets.html"
    model = Ticket
    context_object_name= "tickets"


class TicketDetail(DetailView):
    template_name = "tickets/ticket_detail.html" 
    model = Ticket
