from django.contrib import admin
from django.utils import timezone

from .models import Claim, EmailCode, LocationUpdate, PhoneOTP, Profile, Trip, UserVerification, Vehicle


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'brand', 'vehicle_type', 'price_per_day',
        'location', 'lat_lng', 'registration_number',
        'insurance_status', 'available', 'owner',
    )
    list_filter = ('vehicle_type', 'available', 'brand', 'year')
    search_fields = ('name', 'brand', 'location', 'owner__username', 'registration_number')
    list_editable = ('available',)
    list_per_page = 20

    @admin.display(description='Lat / Lng')
    def lat_lng(self, obj):
        return f'{obj.latitude}, {obj.longitude}'

    @admin.display(description='Insurance')
    def insurance_status(self, obj):
        status = obj.insurance_status
        detail = obj.insurance_valid_until or 'not set'
        if status == 'expired':
            return f'EXPIRED ({detail})'
        if status == 'expiring_soon':
            return f'Expiring ({detail})'
        if status == 'active':
            return f'Active till {detail}'
        return 'Not set'


@admin.register(PhoneOTP)
class PhoneOTPAdmin(admin.ModelAdmin):
    list_display = (
        'phone', 'purpose', 'is_verified', 'is_used',
        'attempts', 'expires_at', 'created_at',
    )
    list_filter = ('purpose', 'is_verified', 'is_used')
    search_fields = ('phone',)
    date_hierarchy = 'created_at'
    readonly_fields = ('phone', 'purpose', 'otp_code_hash', 'expires_at', 'created_at')
    list_per_page = 50

    actions = ['delete_expired']

    @admin.action(description='Delete expired OTPs')
    def delete_expired(self, request, queryset):
        deleted, _ = queryset.filter(expires_at__lt=timezone.now()).delete()
        self.message_user(request, f'{deleted} expired OTP(s) deleted.')


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'email_verified', 'google_sub', 'created_at')
    list_filter = ('email_verified',)
    search_fields = ('user__username', 'user__email', 'phone', 'google_sub')


@admin.register(EmailCode)
class EmailCodeAdmin(admin.ModelAdmin):
    list_display = (
        'email', 'purpose', 'channel', 'is_verified', 'is_used',
        'attempts', 'expires_at', 'created_at',
    )
    list_filter = ('purpose', 'channel', 'is_verified', 'is_used')
    search_fields = ('email',)
    date_hierarchy = 'created_at'
    readonly_fields = ('email', 'purpose', 'code_hash', 'expires_at', 'created_at')
    list_per_page = 50

    actions = ['delete_expired']

    @admin.action(description='Delete expired email codes')
    def delete_expired(self, request, queryset):
        deleted, _ = queryset.filter(expires_at__lt=timezone.now()).delete()
        self.message_user(request, f'{deleted} expired email code(s) deleted.')


@admin.register(UserVerification)
class UserVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'has_photo', 'has_licence', 'has_aadhaar', 'reviewed_at')
    list_filter = ('status',)
    search_fields = ('user__username', 'user__email', 'driving_license_no')
    readonly_fields = ('submitted_at', 'aadhaar_masked', 'dl_masked')
    list_per_page = 25

    actions = ['mark_verified', 'mark_rejected']

    @admin.display(description='Photo')
    def has_photo(self, obj):
        return bool(obj.photo)

    @admin.display(description='Licence')
    def has_licence(self, obj):
        return bool(obj.driving_license_image)

    @admin.display(description='Aadhaar')
    def has_aadhaar(self, obj):
        return bool(obj.aadhaar_image)

    @admin.action(description='Mark selected as verified')
    def mark_verified(self, request, queryset):
        updated = queryset.update(
            status=UserVerification.VERIFIED,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )
        self.message_user(request, f'{updated} verification(s) verified.')

    @admin.action(description='Mark selected as rejected')
    def mark_rejected(self, request, queryset):
        updated = queryset.update(
            status=UserVerification.REJECTED,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )
        self.message_user(request, f'{updated} verification(s) rejected.')


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'vehicle', 'renter', 'owner', 'status',
        'start_at', 'end_at', 'total_amount',
    )
    list_filter = ('status', 'start_at')
    search_fields = ('vehicle__name', 'vehicle__registration_number',
                     'renter__username', 'owner__username')
    readonly_fields = ('start_at',)
    list_per_page = 25


@admin.register(LocationUpdate)
class LocationUpdateAdmin(admin.ModelAdmin):
    list_display = ('id', 'vehicle', 'trip', 'latitude', 'longitude',
                    'speed_kmh', 'source', 'created_at')
    list_filter = ('source', 'created_at')
    search_fields = ('vehicle__name', 'vehicle__registration_number')
    readonly_fields = ('created_at',)
    list_per_page = 25


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'vehicle', 'claimant', 'kind', 'status',
        'verified', 'fir_number', 'damage_estimate', 'created_at',
    )
    list_filter = ('kind', 'status', 'verified')
    search_fields = ('vehicle__name', 'claimant__username',
                     'fir_number', 'fir_station')
    readonly_fields = ('created_at', 'verification_label')
    list_per_page = 25

    actions = ['mark_under_review', 'approve_claim', 'reject_claim', 'settle_claim']

    @admin.action(description='Move to under review')
    def mark_under_review(self, request, queryset):
        queryset.update(status=Claim.UNDER_REVIEW)

    @admin.action(description='Approve (verified genuine)')
    def approve_claim(self, request, queryset):
        updated = queryset.update(
            status=Claim.APPROVED,
            verified=True,
            decided_by=request.user,
            decided_at=timezone.now(),
        )
        self.message_user(request, f'{updated} claim(s) approved & verified.')

    @admin.action(description='Reject')
    def reject_claim(self, request, queryset):
        updated = queryset.update(
            status=Claim.REJECTED,
            verified=False,
            decided_by=request.user,
            decided_at=timezone.now(),
        )
        self.message_user(request, f'{updated} claim(s) rejected.')

    @admin.action(description='Settle')
    def settle_claim(self, request, queryset):
        updated = queryset.update(
            status=Claim.SETTLED,
            verified=True,
            decided_by=request.user,
            decided_at=timezone.now(),
        )
        self.message_user(request, f'{updated} claim(s) settled.')