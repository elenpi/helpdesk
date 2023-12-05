from django.db import models
from django.db.models import Count, Avg, F, DurationField, Min, Max, ExpressionWrapper
import csv
from django.utils import timezone
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin

import altair as alt
import datapane as dp
import pandas as pd

from django.views import View
from django.views.generic import ListView, DetailView, UpdateView
from django.views.generic.edit import FormView, CreateView
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse, reverse_lazy
from django.http import Http404, JsonResponse, HttpResponse, HttpResponseRedirect

from .forms import CreateTicket, CustomUserCreationForm, TicketForm, RatingForm
from .models import Ticket, User, Profile


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
    context_object_name = "tickets"

    def get_queryset(self):
        user = self.request.user

        tickets = Ticket.objects.filter(reporter=user, status__in=["open", "in development"])
        if user.profile.is_agent:
            tickets = Ticket.objects.filter(assignee=user, status__in=["open", "in development"])

        # total = len(tickets)
        # return {tickets: tickets, total: total}
        return tickets


class CreateTicketView(LoginRequiredMixin, CreateView):
    model = Ticket
    form_class = CreateTicket
    template_name = "tickets/ticket_creation.html"
    success_url = reverse_lazy('tickets-page')

    def form_valid(self, form):
        form.instance.reporter = self.request.user

        candidate_agents = User.objects.filter(
            profile__is_agent=True,
            profile__expertise=form.instance.category
        )

        candidate_agents = candidate_agents.annotate(
            assigned_ticket_count=models.Count('assigned_tickets')
        ).order_by('assigned_ticket_count')

        if candidate_agents.exists():
            form.instance.assignee = candidate_agents.first()

        return super().form_valid(form)


class TicketList(LoginRequiredMixin, ListView):
    template_name = "tickets/tickets.html"
    model = Ticket
    context_object_name = "tickets"

    def get_queryset(self):

        profile = Profile.objects.get(user=self.request.user)

        if profile.is_agent:
            return Ticket.objects.filter(assignee=self.request.user)
        else:
            return Ticket.objects.filter(reporter=self.request.user)


class TicketDetail(LoginRequiredMixin, DetailView):
    template_name = "tickets/ticket_detail.html"
    model = Ticket

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['rating_form'] = RatingForm(instance=self.object)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = RatingForm(request.POST, instance=self.object)

        if form.is_valid():
            form.save()
            return HttpResponseRedirect(self.request.path_info)

        return self.render_to_response(self.get_context_data(form=form))


class TicketUpdate(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Ticket
    form_class = TicketForm
    template_name = "tickets/ticket_detail_update_form.html"
    success_message = "Ticket updated successfully"

    def get_success_url(self):
        return reverse("ticket-detail-page", kwargs={"pk": self.object.pk})

    def get_form_kwargs(self):
        kwargs = super(TicketUpdate, self).get_form_kwargs()
        kwargs.update(
            {
                'user': self.request.user
            }
        )
        return kwargs


class TicketDelete(LoginRequiredMixin, SuccessMessageMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            ticket = Ticket.objects.get(pk=self.kwargs.get('pk'))
            if ticket.reporter == request.user:
                ticket.delete()
                return JsonResponse('Success', safe=False)
            else:
                raise Http404
        except Ticket.DoesNotExist:
            raise Http404


class TicketStatistics(LoginRequiredMixin, View):
    template_name = 'tickets/ticket_statistics.html'

    def get(self, request, *args, **kwargs):
        open_tickets = Ticket.objects.filter(status="open")
        in_development_tickets = Ticket.objects.filter(status="in development")
        closed_tickets = Ticket.objects.filter(status="closed")

        response_time_data = self.calculate_response_times(in_development_tickets)
        resolution_time_data = self.calculate_resolution_times(closed_tickets)
        avg_resolution_per_category = self.calculate_avg_resolution_per_category()
        avg_rating_closed_tickets = closed_tickets.aggregate(avg_rating=Avg('rating'))
        resolution_time_data_per_ticket = self.calculate_resolution_per_ticket()
        avg_rating_per_assignee = self.calculate_avg_rating_per_assignee()
    

        status_chart = self.generate_pie_chart(Ticket.objects.values('status').annotate(total=Count('status')))
        assignee_chart = self.generate_assignee_bar_chart(Ticket.objects.values('assignee__username').annotate(total=Count('assignee')))
        resolution_time_chart = self.generate_resolution_time_chart(resolution_time_data_per_ticket)
        avg_rating_chart = self.generate_rating_bar_chart(avg_rating_per_assignee, title='Average Rating per Assignee')

        context = {
            'status_json': status_chart.to_json(),
            'assignee_json': assignee_chart.to_json(),
            'resolution_time': resolution_time_data['average_resolution_time'].days,
            'min_resolution_time': resolution_time_data['min_resolution_time'].days,
            'max_resolution_time': resolution_time_data['max_resolution_time'].days,
            'response_time': response_time_data['average_response_time'].days,
            'min_response_time': response_time_data['min_response_time'].days,
            'max_response_time': response_time_data['max_response_time'].days,
            'avg_rating_closed_tickets': avg_rating_closed_tickets['avg_rating'], 
            'resolution_json': resolution_time_chart.to_json(),
            'avg_rating_per_assignee_json': avg_rating_chart.to_json()
        }

        return render(request, self.template_name, context)

    def calculate_response_times(self, queryset):
        response_times = queryset.annotate(response_time=F('time_in_development') - F('time_created'))
        return response_times.aggregate(
            average_response_time=Avg('response_time'),
            min_response_time=Min('response_time'),
            max_response_time=Max('response_time')
        )

    def calculate_resolution_times(self, queryset):
        resolution_times = queryset.annotate(resolution_time=F('time_closed') - F('time_created'))
        return resolution_times.aggregate(
            average_resolution_time=Avg('resolution_time'),
            min_resolution_time=Min('resolution_time'),
            max_resolution_time=Max('resolution_time')
        )

    def calculate_avg_resolution_per_category(self):
        avg_resolution_per_category = Ticket.objects.values('category').annotate(
            avg_resolution_time=Avg(
                ExpressionWrapper(F('time_closed') - F('time_created'), output_field=DurationField())
            )
        )

        return [
            {'category': entry['category'], 'avg_resolution_time': entry['avg_resolution_time'].total_seconds() / 86400}
            for entry in avg_resolution_per_category
        ]

    def calculate_resolution_per_ticket(self):
        resolution_per_ticket = Ticket.objects.values('category', 'id').annotate(
            resolution_time=ExpressionWrapper(F('time_closed') - F('time_created'), output_field=DurationField()),
        )

        return [
            {
                'category': entry['category'],
                'ticket_id': entry['id'],
                'resolution_time': entry['resolution_time'].total_seconds() / 86400 if entry[
                                                                                           'resolution_time'] is not None else None,
            } for entry in resolution_per_ticket
        ]
    def calculate_avg_rating_per_assignee(self):
        avg_rating_per_assignee = Ticket.objects.values('assignee__username').annotate(
            avg_rating=Avg('rating')
        )

        return [
            {
                'assignee': entry['assignee__username'],
                'avg_rating': entry['avg_rating'] if entry['avg_rating'] is not None else 0
            }
            for entry in avg_rating_per_assignee
        ]
    
    def generate_rating_bar_chart(self, data, title=''):
        chart = alt.Chart(pd.DataFrame(data)).mark_bar().encode(
            alt.X('avg_rating:Q', axis=alt.Axis(title='Average Rating')),
            alt.Y('assignee:N', title='Assignee'),
        ).properties(
            title=title
        )
        return chart

    def generate_pie_chart(self, data):
        chart = alt.Chart(pd.DataFrame(data)).mark_arc().encode(
            theta='total:Q',
            color='status:N'
        )
        return chart

    def generate_assignee_bar_chart(self, data):
        chart = alt.Chart(pd.DataFrame(data)).mark_bar().encode(
            alt.X('total:Q', axis=alt.Axis(title='Total')),
            alt.Y('assignee__username:N', title='Mpla by category')
        )
        return chart

    def generate_resolution_time_chart(self, data):
        chart = alt.Chart(pd.DataFrame(data)).mark_point().encode(
            x='category:N',
            y='resolution_time:Q',
            color='category:N',
            tooltip=['resolution_time:Q']
        ).properties(
            title='Resolution Time per Ticket'
        )
        return chart


class Reports(LoginRequiredMixin, View):
    template_name = 'reports/report.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        timespan = request.POST.get('timespan')

        if timespan == 'daily':
            period = 'days'
        elif timespan == 'weekly':
            period = 'weeks'
        elif timespan == 'monthly':
            period = 'months'
        else:
            return HttpResponse("Invalid timespan")
        
        # Create a CSV file with the report data
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{timespan}_report.csv"'

        writer = csv.writer(response)
        writer.writerow(['Period', 'Total Tickets', 'Total Tickets Closed', 'Total Tickets In Development', 'Total Tickets Open', 'Most Common Category', 'Avg Resolution Time', 'Avg Response Time', 'Most Assigned Agent', 'Most Resolved Agent', 'Fastest Resolving Agent'])

        today = timezone.now()

        for i in range(3):
            if period == 'days':
                start_date = today - timezone.timedelta(days=i+1)
                end_date = start_date + timezone.timedelta(days=1)
            elif period == 'weeks':
                start_date = today - timezone.timedelta(weeks=i+1)
                end_date = start_date + timezone.timedelta(weeks=1)
            else: # period == 'months'
                start_date = today - timezone.timedelta(weeks=(i+1)*4)
                end_date = start_date + timezone.timedelta(weeks=4)

            totals = self.calculate_totals(start_date, end_date)
            writer.writerow([i+1, *totals])  # i+1 is the period number (1, 2, or 3)

        return response

    def calculate_totals(self, start_date, end_date):
        total_tickets = Ticket.objects.filter(time_created__range=(start_date, end_date)).count()

        total_tickets_closed = Ticket.objects.filter(status="closed", time_closed__range=(start_date, end_date)).count()

        total_tickets_in_development = Ticket.objects.filter(status="in development", time_in_development__range=(start_date, end_date)).count()

        total_tickets_open = total_tickets - total_tickets_in_development - total_tickets_closed

        most_common_category = Ticket.objects.filter(time_created__range=(start_date, end_date))\
            .values('category')\
            .annotate(category_count=Count('category'))\
            .order_by('-category_count')\
            .first()
        category = most_common_category['category'] if most_common_category else '-'

        avg_resolution_time = Ticket.objects.filter(status="closed", time_closed__range=(start_date, end_date))\
            .annotate(duration=ExpressionWrapper(F('time_closed') - F('time_in_development'), output_field=DurationField()))\
            .aggregate(avg_resolution=Avg('duration'))['avg_resolution'] or '-'

        avg_response_time = Ticket.objects.filter(status="in development", time_created__range=(start_date, end_date))\
            .annotate(duration=ExpressionWrapper(F('time_in_development') - F('time_created'), output_field=DurationField()))\
            .aggregate(avg_response=Avg('duration'))['avg_response'] or '-'

        most_assigned_agent = Ticket.objects.filter(time_created__range=(start_date, end_date)).values('assignee__profile__user__username').annotate(count=Count('assignee')).order_by('-count').first()
        most_assigned_agent = most_assigned_agent['assignee__profile__user__username'] if most_assigned_agent else '-'

        fastest_resolving_agent = Ticket.objects.filter(status="closed", time_closed__range=(start_date, end_date))\
            .annotate(duration=ExpressionWrapper(F('time_closed') - F('time_created'), output_field=DurationField()))\
            .values('assignee__profile__user__username')\
            .annotate(avg_resolution=Avg('duration'))\
            .order_by('avg_resolution').first()
        fastest_resolving_agent = fastest_resolving_agent['assignee__profile__user__username'] if fastest_resolving_agent else '-'
        
        most_resolved_agent = Ticket.objects.filter(status="closed", time_closed__range=(start_date, end_date)).values('assignee__profile__user__username').annotate(count=Count('assignee')).order_by('-count').first()
        most_resolved_agent = most_resolved_agent['assignee__profile__user__username'] if most_resolved_agent else '-'

        totals = [total_tickets, total_tickets_closed, total_tickets_in_development, total_tickets_open, category, avg_resolution_time, avg_response_time, most_assigned_agent, most_resolved_agent, fastest_resolving_agent]

        return totals