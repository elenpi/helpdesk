from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.

def index(request):
    return HttpResponse("Hello World!") 

def tickets(request):
    return HttpResponse("My tickets!") 

def ticket_detail(request):
    return HttpResponse("A ticket!") 
