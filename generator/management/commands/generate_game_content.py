
from django.core.management.base import BaseCommand
from generator.service import generate_universe, generate_quest

class Command(BaseCommand):
    help = 'Generate game content based on a person\'s name'

    def add_arguments(self, parser):
        parser.add_argument('person_name', type=str, help='The name of the person to generate content for')

    def handle(self, *args, **options):
        person_name = options['person_name']
        universe_id = generate_universe(person_name)
        generate_quest(universe_id,9)

        self.stdout.write(self.style.SUCCESS(f"Game content for {person_name} has been generated and stored in the database."))