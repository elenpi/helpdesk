from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.Registration.as_view(), name='registration'),
    path("", views.OpenTicketsList.as_view(), name="landing-page"),
    path("tickets/create", views.CreateTicketView.as_view(), name="ticket-creation-page"),
    path("tickets/", views.TicketList.as_view(), name="tickets-page"),
    path("tickets/<int:pk>",views.TicketDetail.as_view(), name="ticket-detail-page"),
    path("tickets/<int:pk>/edit",views.TicketUpdate.as_view(), name="ticket-detail-edit"),
    path("tickets/<int:pk>/delete",views.TicketDelete.as_view(), name="ticket-delete"),
    path("tickets/statistics",views.TicketStatistics.as_view(), name="ticket-statistics"),
    path("tickets/reports/", views.Reports.as_view(), name="ticket-report")
]
