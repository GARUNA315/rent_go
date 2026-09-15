from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


def _vehicle_photo_upload(instance, filename):
    safe = filename.replace(' ', '_')
    unique = uuid.uuid4().hex[:10]
    return f'vehicles/{instance.pk or "new"}/photos/{unique}_{safe}'


def _rc_upload(instance, filename):
    return f'vehicles/{instance.pk or "new"}/rc/{filename}'


def _insurance_upload(instance, filename):
    return f'vehicles/{instance.pk or "new"}/insurance/{filename}'


def _verification_upload(instance, filename):
    return f'verification/{instance.user_id or "new"}/{filename}'


def _claim_upload(instance, filename):
    return f'claims/{instance.pk or "new"}/photos/{filename}'


def _fir_upload(instance, filename):
    return f'claims/{instance.pk or "new"}/fir/{filename}'


class Vehicle(models.Model):
    CAR = 'car'
    BIKE = 'bike'

    VEHICLE_TYPES = [
        (CAR, 'Car'),
        (BIKE, 'Bike'),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vehicles',
        verbose_name='Owner',
    )

    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=50)
    vehicle_type = models.CharField(max_length=10, choices=VEHICLE_TYPES)
    year = models.PositiveIntegerField(default=2020)

    price_per_day = models.DecimalField(max_digits=8, decimal_places=2)

    location = models.CharField(
        max_length=150,
        help_text='City / area where the vehicle is available',
    )

    latitude = models.FloatField(default=0)
    longitude = models.FloatField(default=0)

    image = models.CharField(
        max_length=255,
        blank=True,
        help_text='Relative media path or URL of the vehicle photo',
    )

    photo = models.ImageField(
        upload_to=_vehicle_photo_upload,
        blank=True,
        null=True,
        help_text='Upload a clear photo of your vehicle.',
    )

    description = models.TextField(blank=True)
    available = models.BooleanField(default=True)

    # --- Owner-provided legal documents & safety details ------------------
    registration_number = models.CharField(
        max_length=20,
        blank=True,
        help_text='RC / registration number, e.g. MH01AB1234',
    )
    rc_image = models.ImageField(
        upload_to=_rc_upload,
        blank=True,
        null=True,
        help_text='Uploaded registration certificate (RC) photo.',
    )
    insurance_number = models.CharField(
        max_length=40,
        blank=True,
        help_text='Policy number of the vehicle insurance.',
    )
    insurance_provider = models.CharField(
        max_length=60,
        blank=True,
        help_text='Insurance company name.',
    )
    insurance_valid_until = models.DateField(
        null=True,
        blank=True,
        help_text='Insurance validity end date — used to check if the policy '
                  'is still active.',
    )
    insurance_image = models.ImageField(
        upload_to=_insurance_upload,
        blank=True,
        null=True,
        help_text='Uploaded insurance certificate photo.',
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.brand} {self.name} ({self.vehicle_type})'

    @property
    def insurance_status(self):
        """'active', 'expiring_soon', 'expired' or 'not_set'."""
        if not self.insurance_valid_until:
            return 'not_set'
        today = timezone.localdate()
        if self.insurance_valid_until < today:
            return 'expired'
        if (self.insurance_valid_until - today).days <= 30:
            return 'expiring_soon'
        return 'active'

    @property
    def active_trip(self):
        return self.trips.filter(status=Trip.ACTIVE).order_by('-start_at').first()

    def distance_km(self, lat, lng):
        """Haversine distance in kilometres from a given point."""
        from math import radians, cos, sin, asin, sqrt

        lat1, lng1 = radians(self.latitude), radians(self.longitude)
        lat2, lng2 = radians(float(lat)), radians(float(lng))

        d_lat = lat2 - lat1
        d_lng = lng2 - lng1

        a = (sin(d_lat / 2) ** 2
             + cos(lat1) * cos(lat2) * sin(d_lng / 2) ** 2)

        return 2 * 6371 * asin(sqrt(a))


class PhoneOTP(models.Model):
    """A one-time password sent to a mobile number."""

    LOGIN = 'login'
    SIGNUP = 'signup'

    PURPOSES = [
        (LOGIN, 'Login'),
        (SIGNUP, 'Signup'),
    ]

    SMS = 'sms'
    EMAIL = 'email'
    INAPP = 'inapp'

    CHANNELS = [
        (SMS, 'SMS'),
        (EMAIL, 'Email'),
        (INAPP, 'In-app (no SMS)'),
    ]

    phone = models.CharField(
        max_length=15,
        db_index=True,
        help_text='Phone number normalised with country code, e.g. 919876543210',
    )
    purpose = models.CharField(max_length=10, choices=PURPOSES)
    otp_code_hash = models.CharField(max_length=128)
    channel = models.CharField(
        max_length=10,
        choices=CHANNELS,
        default=INAPP,
        help_text='How the OTP was delivered.',
    )
    is_verified = models.BooleanField(default=False)
    is_used = models.BooleanField(
        default=False,
        help_text='OTP already consumed to log in or create an account.',
    )
    expires_at = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.phone} ({self.purpose})'

    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() >= self.expires_at


class Profile(models.Model):
    """Extra details attached to a user account."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    phone = models.CharField(
        max_length=15,
        unique=True,
        blank=True,
        null=True,
        db_index=True,
        help_text='Verified mobile number, e.g. 919876543210 '
                 '(blank for Google / email-only accounts).',
    )
    email_verified = models.BooleanField(
        default=False,
        help_text='True once the address on user.email has been verified '
                  'via an email code or Google account.',
    )
    google_sub = models.CharField(
        max_length=64,
        unique=True,
        blank=True,
        null=True,
        help_text='Google account subject ID (unique across all Google users).',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} ({self.phone or "no phone"})'


class EmailCode(models.Model):
    """A one-time code sent to an email address for verification.

    Only the hash is stored — the plain code is delivered via SMTP (or the
    console in development) and never persisted.
    """

    VERIFY = 'verify'

    PURPOSES = [
        (VERIFY, 'Verify email'),
    ]

    SMTP = 'smtp'
    CONSOLE = 'console'

    CHANNELS = [
        (SMTP, 'SMTP email'),
        (CONSOLE, 'Console (dev)'),
    ]

    email = models.EmailField(
        max_length=254,
        db_index=True,
        help_text='Normalised (lowercased) verified-at delivery address.',
    )
    purpose = models.CharField(max_length=10, choices=PURPOSES)
    code_hash = models.CharField(max_length=128)
    channel = models.CharField(
        max_length=10,
        choices=CHANNELS,
        default=CONSOLE,
        help_text='How the code was delivered.',
    )
    is_verified = models.BooleanField(default=False)
    is_used = models.BooleanField(
        default=False,
        help_text='Code already consumed (email verified → account created).',
    )
    expires_at = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.email} ({self.purpose})'

    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() >= self.expires_at


class UserVerification(models.Model):
    """KYC documents for a user: photo, driving licence and Aadhaar.

    Files are stored under media/verification/. Aadhaar numbers are only
    displayed masked — full values are never shown back to the UI.
    """

    PENDING = 'pending'
    VERIFIED = 'verified'
    REJECTED = 'rejected'

    STATUS = [
        (PENDING, 'Pending review'),
        (VERIFIED, 'Verified'),
        (REJECTED, 'Rejected'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='verification',
    )
    photo = models.ImageField(
        upload_to=_verification_upload,
        blank=True,
        null=True,
        help_text='A clear, recent photo of yourself.',
    )
    driving_license_no = models.CharField(
        max_length=32,
        blank=True,
        help_text='Driving licence number as printed on the card.',
    )
    driving_license_image = models.ImageField(
        upload_to=_verification_upload,
        blank=True,
        null=True,
        help_text='Front & back photo of the driving licence.',
    )
    aadhaar_no = models.CharField(
        max_length=12,
        blank=True,
        help_text='12-digit Aadhaar number (stored, displayed masked).',
    )
    aadhaar_image = models.ImageField(
        upload_to=_verification_upload,
        blank=True,
        null=True,
        help_text='Aadhaar card photo (masked version recommended).',
    )
    status = models.CharField(max_length=10, choices=STATUS, default=PENDING)
    review_note = models.CharField(
        max_length=200,
        blank=True,
        help_text='Public note left by the reviewer.',
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='verification_reviews',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f'{self.user.username} → {self.status}'

    @property
    def is_verified(self):
        return self.status == self.VERIFIED

    @property
    def aadhaar_masked(self):
        """Only ever expose the last 4 digits."""
        digits = ''.join(ch for ch in self.aadhaar_no if ch.isdigit())
        if not digits:
            return ''
        if len(digits) <= 4:
            return '****' + digits[-len(digits):]
        return '**** **** **' + digits[-4:]

    @property
    def dl_masked(self):
        base = self.driving_license_no.strip()
        if not base:
            return ''
        if len(base) <= 6:
            return '*' * min(len(base), 6)
        return '*' * (len(base) - 6) + base[-6:]


class Trip(models.Model):
    """A rental trip. While active, its GPS pings power live tracking."""

    ACTIVE = 'active'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'

    STATUS = [
        (ACTIVE, 'Active'),
        (COMPLETED, 'Completed'),
        (CANCELLED, 'Cancelled'),
    ]

    renter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='trips_as_renter',
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='trips_as_owner',
        help_text='Snapshot of the vehicle owner when the trip started.',
    )
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='trips',
    )
    status = models.CharField(max_length=10, choices=STATUS, default=ACTIVE)
    start_at = models.DateTimeField(auto_now_add=True)
    end_at = models.DateTimeField(null=True, blank=True)
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Final billable amount (set by the owner on completion).',
    )
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['-start_at']

    def __str__(self):
        return f'{self.vehicle} @ {self.renter.username} ({self.status})'

    @property
    def is_active(self):
        return self.status == self.ACTIVE


class LocationUpdate(models.Model):
    """One GPS ping belonging to an active trip."""

    GPS = 'gps'
    SIMULATED = 'simulated'

    SOURCES = [
        (GPS, 'GPS device'),
        (SIMULATED, 'Simulated demo'),
    ]

    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name='updates',
    )
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='location_updates',
    )
    latitude = models.FloatField()
    longitude = models.FloatField()
    speed_kmh = models.FloatField(default=0)
    heading = models.FloatField(default=0)
    accuracy_m = models.FloatField(default=0)
    source = models.CharField(max_length=10, choices=SOURCES, default=GPS)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.vehicle} @ ({self.latitude:.4f}, {self.longitude:.4f})'


class Claim(models.Model):
    """Risk / insurance claim filed by a user against a rental.

    The "FIR verification" flow: the claimant provides FIR details and a copy,
    then a staff reviewer decides whether the claim is genuine (verified True)
    or not, and approves / rejects / settles it.
    """

    ACCIDENT = 'accident'
    DAMAGE = 'damage'
    THEFT = 'theft'
    BREAKDOWN = 'breakdown'

    KIND = [
        (ACCIDENT, 'Accident'),
        (DAMAGE, 'Damage'),
        (THEFT, 'Theft'),
        (BREAKDOWN, 'Breakdown'),
    ]

    FILED = 'filed'
    UNDER_REVIEW = 'under_review'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    SETTLED = 'settled'

    STATUS = [
        (FILED, 'Filed'),
        (UNDER_REVIEW, 'Under review'),
        (APPROVED, 'Approved for payout'),
        (REJECTED, 'Rejected'),
        (SETTLED, 'Settled'),
    ]

    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE,
                                related_name='claims')
    trip = models.ForeignKey(
        Trip,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='claims',
        help_text='The rental trip this claim relates to (if any).',
    )
    claimant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='claims',
    )
    kind = models.CharField(max_length=10, choices=KIND)
    description = models.TextField()
    incident_at = models.DateTimeField()
    incident_location = models.CharField(max_length=150, blank=True)
    latitude = models.FloatField(default=0)
    longitude = models.FloatField(default=0)
    damage_estimate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    photo = models.ImageField(upload_to=_claim_upload, blank=True, null=True)
    photo2 = models.ImageField(upload_to=_claim_upload, blank=True, null=True)
    fir_number = models.CharField(
        max_length=40,
        blank=True,
        help_text='First Information Report (FIR) number from the police station.',
    )
    fir_station = models.CharField(
        max_length=100,
        blank=True,
        help_text='Police station where the FIR was registered.',
    )
    fir_image = models.ImageField(
        upload_to=_fir_upload,
        blank=True,
        null=True,
        help_text='Copy of the FIR document.',
    )
    status = models.CharField(max_length=15, choices=STATUS, default=FILED)
    verified = models.BooleanField(
        default=False,
        help_text='Staff-verified as genuine (docs + FIR cross-checked).',
    )
    decision_note = models.TextField(blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='claim_decisions',
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'#{self.pk} {self.get_kind_display()} — {self.vehicle}'

    @property
    def verification_label(self):
        if self.verified:
            return 'Verified genuine'
        if self.status == Claim.REJECTED:
            return 'Rejected'
        return 'Pending verification'