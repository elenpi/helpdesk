from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils.text import slugify
from ...models import Profile, Expertise, Ticket, Status
import random

class Command(BaseCommand):
    help = 'Create random tickets'

    def handle(self, *args, **options):
        self.stdout.write('Starting to create reporters and tickets...')

        expertise_values = [e.value for e in Expertise]
        status_values = [s.value for s in Status]

        for i in range(20):
            # Creating a reporter user
            username = f'user_{slugify(str(i))}'
            if User.objects.filter(username=username).exists():
               self.stdout.write('User already exists: ' + username)
               next
                
            reporter_user = User.objects.create_user(username=username, password='testpassword')
            
            # Creating a reporter profile
            Profile.objects.create(user=reporter_user, is_agent=False, expertise=random.choice(expertise_values))

            for j in range(3):
                # For each reporter create 3 tickets
                Ticket.objects.create(
                    title=f'Ticket {j} of user {username}',
                    description=f'This is ticket {j} of user {username}',
                    status=random.choice(status_values),
                    category=random.choice(expertise_values),
                    reporter=reporter_user,
                )

        self.stdout.write('Finished creating reporters and tickets.')