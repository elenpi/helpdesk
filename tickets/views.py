from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.

def index(request):
    return render(request, "tickets/index.html") 

def create_ticket(request):
    return HttpResponse("New ticket!") 

def tickets(request):
    return render(request, "tickets/tickets.html")

def ticket_detail(request):
    return HttpResponse("A ticket!") 
