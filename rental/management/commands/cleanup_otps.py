from django.core.management.base import BaseCommand
from django.utils import timezone

from rental.models import PhoneOTP


class Command(BaseCommand):
    help = 'Delete expired or consumed OTP records from the database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--older-than-days',
            type=int,
            default=1,
            help='Only delete OTPs created later than N days ago too (default: 1).',
        )

    def handle(self, *args, **options):
        cutoff = timezone.now() - timezone.timedelta(days=options['older_than_days'])

        expired = PhoneOTP.objects.filter(expires_at__lt=timezone.now())
        stale = PhoneOTP.objects.filter(
            is_used=True,
            created_at__lt=cutoff,
        )

        expired_count = expired.count()
        stale_count = stale.count()

        expired.delete()
        stale.delete()

        self.stdout.write(self.style.SUCCESS(
            f'Deleted {expired_count} expired and {stale_count} stale OTP records.'
        ))