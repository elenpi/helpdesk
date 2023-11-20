from django.contrib import admin
from .models import Profile, Expertise, Status, Ticket
from django.contrib.auth.models import User


# Register your models here.


class ProfileAdmin(admin.ModelAdmin):
    list_display = ('username', 'first_name', 'last_name', 'is_agent', 'expertise')

    def username(self, obj):
        return obj.user.username

    username.short_description = 'username'

    def first_name(self, obj):
        return obj.user.first_name

    first_name.short_description = 'first name'

    def last_name(self, obj):
        return obj.user.last_name

    last_name.short_description = 'last name'


class TicketAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'category', 'reporter_username',
                    'assignee_username', 'time_created', 'time_in_development', 'time_closed', 'rating')

    def reporter_username(self, obj):
        return obj.reporter.username

    reporter_username.short_description = 'reporter'

    def assignee_username(self, obj):
        return obj.assignee.username if obj.assignee else None

    assignee_username.short_description = 'assignee'


admin.site.register(Profile, ProfileAdmin)
admin.site.register(Ticket, TicketAdmin)
