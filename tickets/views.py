from django.db import models
from django.db.models import Count, Avg, F, DurationField, Min, Max, ExpressionWrapper
import csv
from django.utils import timezone
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from dateutil.relativedelta import relativedelta


import altair as alt
import datapane as dp
import pandas as pd
import datetime, time

from django.views import View
from django.views.generic import ListView, DetailView, UpdateView
from django.views.generic.edit import FormView, CreateView
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse, reverse_lazy
from django.http import Http404, JsonResponse, HttpResponse, HttpResponseRedirect

from .forms import CreateTicket, CustomUserCreationForm, TicketForm, RatingForm
from .models import Ticket, User, Profile, Status


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ticket_count'] = self.get_queryset().count()
        return context

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

    def stringify_timedelta(self, td):
        days, remainder = divmod(td.seconds + td.days * 86400, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        if days > 0:
            return '%d d, %d h, %d m' % (days, hours, minutes)
        elif hours > 0:
            return '%d h, %d m' % (hours, minutes)
        elif minutes > 0:
            return '%d m, %d s' % (minutes, seconds)
        else:
            return '%d s' % (seconds)


    def get(self, request, *args, **kwargs):
        in_development_tickets = Ticket.objects.filter(status="in development")
        closed_tickets = Ticket.objects.filter(status="closed")

        response_time_data = self.calculate_response_times(in_development_tickets)
        resolution_time_data = self.calculate_resolution_times(closed_tickets)
        avg_resolution_per_category = self.calculate_avg_resolution_per_category()
        avg_rating_closed_tickets = closed_tickets.aggregate(avg_rating=Avg('rating'))
        resolution_time_data_per_ticket = self.calculate_resolution_per_ticket()
        avg_rating_per_assignee = self.calculate_avg_rating_per_assignee()
        tickets_per_category = self.calculate_tickets_per_category()
        resolution_time_per_ticket = self.calculate_resolution_time_per_ticket()
        pending_tickets = Ticket.objects.filter(status="in development").count()
        open_tickets = Ticket.objects.filter(status=Status.OPEN.value).count()

        status_chart = self.generate_pie_chart(Ticket.objects.values('status').annotate(total=Count('status')))
        assignee_chart = self.generate_assignee_bar_chart(Ticket.objects.values('assignee__username').annotate(total=Count('assignee')))
        resolution_time_chart = self.generate_resolution_time_chart(resolution_time_data_per_ticket)
        avg_rating_chart = self.generate_rating_bar_chart(avg_rating_per_assignee, title='Average Rating per Assignee')
        tickets_per_category_chart = self.generate_tickets_per_category_chart(tickets_per_category)
        resolution_time_per_ticket_chart = self.generate_resolution_time_per_ticket_chart(resolution_time_per_ticket)

        

        context = {
            'status_json': status_chart.to_json(),
            'assignee_json': assignee_chart.to_json(),
            'resolution_time': self.stringify_timedelta(resolution_time_data['average_resolution_time']),
            'min_resolution_time': self.stringify_timedelta(resolution_time_data['min_resolution_time']),
            'max_resolution_time': self.stringify_timedelta(resolution_time_data['max_resolution_time']),
            'response_time': self.stringify_timedelta(response_time_data['average_response_time']),
            'min_response_time': self.stringify_timedelta(response_time_data['min_response_time']),
            'max_response_time': self.stringify_timedelta(response_time_data['max_response_time']),
            'open_tickets': open_tickets,
            'pending_tickets': pending_tickets,
            'avg_rating_closed_tickets': avg_rating_closed_tickets['avg_rating'], 
            'resolution_json': resolution_time_chart.to_json(),
            'avg_rating_per_assignee_json': avg_rating_chart.to_json(),
            'tickets_per_category_json': tickets_per_category_chart.to_json(),
            'resolution_time_per_ticket_json': resolution_time_per_ticket_chart.to_json()
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
    
    def calculate_tickets_per_category(self):
        tickets_per_category = Ticket.objects.values(
            'category').annotate(total=Count('category'))

        return [
            {'category': entry['category'], 'total': entry['total']}
            for entry in tickets_per_category
        ]
    
    
    def calculate_resolution_time_per_ticket(self):
        tickets = Ticket.objects.values('assignee__username', 'time_created', 'time_closed')

        data = []
        for ticket in tickets:
            if ticket['time_closed'] and ticket['time_created']:
                resolution_time = ticket['time_closed'] - ticket['time_created']
                data.append({'assignee_username': ticket['assignee__username'], 'resolution_time': resolution_time.total_seconds() / 86400})

        return data

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
            color='status:N',
            tooltip=['total', 'status']
        ).properties(
            title='Number of Tickets Per Status'
        )
        return chart

    def generate_assignee_bar_chart(self, data):
        chart = alt.Chart(pd.DataFrame(data)).mark_bar().encode(
            alt.X('total:Q', axis=alt.Axis(title='Total Number of Tickets')),
            alt.Y('assignee__username:N', title='Asignee')
        ).properties(
            title='Total Number of Tickets per Asingee'
        )
        return chart

    def generate_resolution_time_chart(self, data):
        chart = alt.Chart(pd.DataFrame(data)).mark_point().encode(
            x='category:N',
            y=alt.Y('resolution_time:Q', title='Resolution Time (days)'),
            color='category:N',
            tooltip=[
                alt.Tooltip('resolution_time:Q', title='Resolution Time', format='.0f'),
                'category:N'
            ]
        ).properties(
            title='Resolution Time per Category'
        )
        return chart
    
    def generate_tickets_per_category_chart(self, data):
        chart = alt.Chart(pd.DataFrame(data)).mark_bar().encode(
            alt.X('total:Q', axis=alt.Axis(title='Total Number of Tickets')),
            alt.Y('category:N', title='Category')
        ).properties(
            title='Total Number of Tickets per Category'
        )
        return chart
    
    def generate_resolution_time_per_ticket_chart(self, data):
        chart = alt.Chart(pd.DataFrame(data)).mark_point().encode(
            alt.Y('assignee_username:N', title='Agent Name'),
            alt.X('resolution_time:Q', axis=alt.Axis(title='Resolution Time (days)'))
        ).properties(
            title='Resolution Time per Ticket per Agent'
        )
        return chart


class Reports(LoginRequiredMixin, View):
    template_name = 'reports/report.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        timespan = request.POST.get('timespan')

        if timespan == 'daily':
            period = timezone.timedelta(days=1)
        elif timespan == 'weekly':
            period = timezone.timedelta(weeks=1)
        else:  # 'monthly'
            period = relativedelta(months=1)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{timespan}_report.csv"'

        writer = csv.writer(response)
        writer.writerow(['Timespan (Start Date)', 'Total Tickets', 'Total Tickets In Development', 'Total Tickets Closed',
                         'Avg Response Time', 'Avg Resolution Time', 'Avg Rating', 'Most Assigned Agent',
                         'Most Responded Agent'])

        end_date = timezone.now()
        for i in range(3):
            start_date = end_date - period

            total_tickets = self.total_tickets(start_date, end_date)
            total_tickets_in_dev = self.total_tickets_in_dev(start_date, end_date)
            total_tickets_closed = self.total_tickets_closed(start_date, end_date)

            avg_response_time = self.format_duration(self.avg_response_time(start_date, end_date))
            avg_resolution_time = self.format_duration(self.avg_resolution_time(start_date, end_date))

            avg_rating = self.avg_rating(start_date, end_date)
            avg_rating = "{:.2f}".format(avg_rating) if avg_rating is not None else "-"
            
            most_assigned_agent = self.most_assigned_agent(start_date, end_date)
            most_responded_agent = self.most_responded_agent(start_date, end_date)

            writer.writerow([start_date.strftime('%Y-%m-%d %H:%M:%S'), total_tickets, total_tickets_in_dev, total_tickets_closed, avg_response_time,
                             avg_resolution_time, avg_rating, most_assigned_agent, most_responded_agent])

            end_date = start_date

        return response

    def total_tickets(self, start_date, end_date):
        return Ticket.objects.filter(time_created__range=[start_date, end_date]).count()

    def total_tickets_in_dev(self, start_date, end_date):
        return Ticket.objects.filter(status=Status.IN_DEVELOPMENT.value, time_in_development__range=[start_date, end_date]).count()

    def total_tickets_closed(self, start_date, end_date):
        return Ticket.objects.filter(status=Status.CLOSED.value, time_closed__range=[start_date, end_date]).count()

    def avg_response_time(self, start_date, end_date):
        durations = Ticket.objects.filter(time_in_development__range=[start_date, end_date]).annotate(
            duration=F('time_in_development') - F('time_created')).values_list('duration', flat=True)

        return self.calculate_avg_duration(durations)

    def avg_resolution_time(self, start_date, end_date):
        durations = Ticket.objects.filter(time_closed__range=[start_date, end_date]).annotate(
            duration=F('time_closed') - F('time_created')).values_list('duration', flat=True)

        return self.calculate_avg_duration(durations)

    @staticmethod
    def calculate_avg_duration(durations):
        total_seconds = sum(d.total_seconds() for d in durations if d is not None)
        count = sum(1 for d in durations if d is not None)
        avg_seconds = total_seconds / count if count > 0 else 0
        return datetime.timedelta(seconds=avg_seconds)

    def avg_rating(self, start_date, end_date):
        return Ticket.objects.filter(time_closed__range=[start_date, end_date]).aggregate(
            avg_rating=Avg('rating'))['avg_rating']

    def most_assigned_agent(self, start_date, end_date):
        return Ticket.objects.filter(time_created__range=[start_date, end_date]).values('assignee__username').annotate(
            count=Count('assignee')).order_by('-count').values_list('assignee__username', flat=True).first()

    def most_responded_agent(self, start_date, end_date):
        return Ticket.objects.filter(time_in_development__range=[start_date, end_date]).values(
            'assignee__username').annotate(count=Count('assignee')).order_by('-count').values_list(
            'assignee__username', flat=True).first()

    @staticmethod
    def format_duration(td):
        days, seconds = td.days, td.seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        return f"{days}d:{hours}h:{minutes}m:{seconds}s"
