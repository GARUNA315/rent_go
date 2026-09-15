from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from rental.models import Vehicle

USER_MODEL = get_user_model()

VEHICLES = [
    {
        'name': 'Swift',
        'brand': 'Maruti Suzuki',
        'vehicle_type': Vehicle.CAR,
        'year': 2021,
        'price_per_day': '1200',
        'location': 'Pune',
        'latitude': 18.5204,
        'longitude': 73.8567,
        'image': '/static/rental/images/car-card.png',
        'description': 'Comfortable hatchback, great mileage, ideal for city trips.',
        'available': True,
    },
    {
        'name': 'Verna',
        'brand': 'Hyundai',
        'vehicle_type': Vehicle.CAR,
        'year': 2022,
        'price_per_day': '1800',
        'location': 'Mumbai',
        'latitude': 19.0760,
        'longitude': 72.8777,
        'image': '/static/rental/images/verna.png',
        'description': 'Sporty sedan with premium interior and smooth highway drive.',
        'available': True,
    },
    {
        'name': 'Creta',
        'brand': 'Hyundai',
        'vehicle_type': Vehicle.CAR,
        'year': 2023,
        'price_per_day': '2200',
        'location': 'Mumbai',
        'latitude': 19.1286,
        'longitude': 72.8367,
        'image': '/static/rental/images/car-card.png',
        'description': 'Spacious SUV, perfect for family road trips.',
        'available': True,
    },
    {
        'name': 'Activa',
        'brand': 'Honda',
        'vehicle_type': Vehicle.BIKE,
        'year': 2020,
        'price_per_day': '300',
        'location': 'Pune',
        'latitude': 18.5679,
        'longitude': 73.9143,
        'image': '/static/rental/images/bike-card.png',
        'description': 'Easy-to-ride scooter for quick city commutes.',
        'available': True,
    },
    {
        'name': 'Bullet 350',
        'brand': 'Royal Enfield',
        'vehicle_type': Vehicle.BIKE,
        'year': 2019,
        'price_per_day': '900',
        'location': 'Delhi',
        'latitude': 28.6139,
        'longitude': 77.2090,
        'image': '/static/rental/images/bullet.png',
        'description': 'Classic Royal Enfield with a powerful thump and vintage style.',
        'available': True,
    },
    {
        'name': 'Nexon EV',
        'brand': 'Tata',
        'vehicle_type': Vehicle.CAR,
        'year': 2023,
        'price_per_day': '2500',
        'location': 'Delhi',
        'latitude': 28.5355,
        'longitude': 77.3910,
        'image': '/static/rental/images/car-card.png',
        'description': 'Electric SUV — eco friendly, silent, and loaded with features.',
        'available': True,
    },
    {
        'name': 'Duke 200',
        'brand': 'KTM',
        'vehicle_type': Vehicle.BIKE,
        'year': 2021,
        'price_per_day': '1100',
        'location': 'Bengaluru',
        'latitude': 12.9716,
        'longitude': 77.5946,
        'image': '/static/rental/images/bike-card.png',
        'description': 'Aggressive performance bike, made for adrenaline rides.',
        'available': True,
    },
    {
        'name': 'Swift Dzire',
        'brand': 'Maruti Suzuki',
        'vehicle_type': Vehicle.CAR,
        'year': 2020,
        'price_per_day': '1400',
        'location': 'Bengaluru',
        'latitude': 12.9250,
        'longitude': 77.5938,
        'image': '/static/rental/images/car-card.png',
        'description': 'Comfortable sedan, great for outstation trips with luggage.',
        'available': True,
    },
]


class Command(BaseCommand):
    help = 'Seed the database with demo users and vehicles.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing vehicles before seeding.',
        )

    def handle(self, *args, **options):
        if options['reset']:
            Vehicle.objects.all().delete()
            self.stdout.write('Deleted existing vehicles.')

        owner, created = USER_MODEL.objects.get_or_create(
            username='demo_owner',
            defaults={
                'first_name': 'Demo',
                'last_name': 'Owner',
                'email': 'owner@rentgo.in',
                'is_staff': True,
            },
        )
        if created:
            owner.set_password('demo@1234')
            owner.save()
            self.stdout.write(self.style.SUCCESS('Created demo owner user.'))

        created_count = 0
        for data in VEHICLES:
            label = f"{data['brand']} {data['name']}"
            if Vehicle.objects.filter(brand=data['brand'], name=data['name']).exists():
                self.stdout.write(f'Skipped (already exists): {label}')
                continue
            Vehicle.objects.create(owner=owner, **data)
            created_count += 1
            self.stdout.write(f'Seeded: {label}')

        self.stdout.write(self.style.SUCCESS(
            f'Done. {created_count} vehicle(s) added, '
            f'{Vehicle.objects.count()} total.'
        ))