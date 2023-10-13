from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="landing-page"),
    path("tickets", views.tickets, name="tickets-page"),
    path("tickets/<slug:slug",views.ticket_detail, name="ticket-detail-page")
]
