from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path("", views.OpenTicketsList.as_view(), name="landing-page"),
    path("tickets/create", views.CreateTicketView.as_view(), name="ticket-creation-page"),
    path("tickets/", views.TicketList.as_view(), name="tickets-page"),
    path("tickets/<int:pk>",views.TicketDetail.as_view(), name="ticket-detail-page")
]
