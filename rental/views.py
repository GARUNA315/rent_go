from django.contrib import messages
from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import ClaimForm, LoginForm, RegisterForm, VerificationForm, VehicleForm
from .models import Claim, EmailCode, LocationUpdate, PhoneOTP, Profile, Trip, UserVerification, Vehicle
from . import email_service, otp_service


def _parse_coords(request):
    """Return (lat, lng, has_coords) from query string or session."""
    try:
        lat = request.GET.get('lat') or request.session.get('lat')
        lng = request.GET.get('lng') or request.session.get('lng')
        if lat is None or lng is None:
            return 0, 0, False
        return float(lat), float(lng), True
    except (TypeError, ValueError):
        return 0, 0, False


def _vehicle_list(request):
    vehicles = Vehicle.objects.filter(available=True)

    vehicle_type = request.GET.get('type', '').strip()
    location = request.GET.get('location', '').strip()
    query = request.GET.get('q', '').strip()

    if vehicle_type in ('car', 'bike'):
        vehicles = vehicles.filter(vehicle_type=vehicle_type)

    if location or query:
        term = location or query
        vehicles = vehicles.filter(location__icontains=term)

    lat, lng, has_coords = _parse_coords(request)

    if has_coords:
        vehicles = sorted(
            vehicles,
            key=lambda v: v.distance_km(lat, lng),
        )
        for v in vehicles:
            v.distance = round(v.distance_km(lat, lng), 1)
    else:
        vehicles = list(vehicles)

    return vehicles, vehicle_type, location, has_coords


def home(request):
    vehicles, _, _, has_coords = _vehicle_list(request)
    context = {
        'vehicles': vehicles[:4],
        'has_coords': has_coords,
    }
    return render(request, 'rental/index.html', context)


def vehicles(request):
    vehicle_list, vehicle_type, location, has_coords = _vehicle_list(request)
    context = {
        'vehicles': vehicle_list,
        'vehicle_type': vehicle_type,
        'location': location,
        'has_coords': has_coords,
        'count': len(vehicle_list),
    }
    return render(request, 'rental/vehicles.html', context)


def vehicle_detail(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    lat, lng, has_coords = _parse_coords(request)
    distance = round(vehicle.distance_km(lat, lng), 1) if has_coords else None
    owner_verification = UserVerification.objects.filter(
        user=vehicle.owner,
        status=UserVerification.VERIFIED,
    ).first()
    return render(request, 'rental/vehicle_detail.html', {
        'vehicle': vehicle,
        'distance': distance,
        'owner_verified': bool(owner_verification),
        'active_trip': vehicle.active_trip,
    })


@login_required
def add_vehicle(request):
    lat = request.GET.get('lat', '')
    lng = request.GET.get('lng', '')
    location = request.GET.get('location', '')

    initial = {
        'latitude': lat,
        'longitude': lng,
        'location': location,
    }

    if request.method == 'POST':
        form = VehicleForm(request.POST, request.FILES)
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.owner = request.user
            vehicle.save()
            messages.success(
                request,
                f'{vehicle.brand} {vehicle.name} was added successfully!',
            )
            return redirect('vehicle_detail', pk=vehicle.pk)
    else:
        form = VehicleForm(initial=initial)

    return render(request, 'rental/add_vehicle.html', {
        'form': form,
        'has_coords': bool(lat and lng),
    })


def auth_page(request, mode=None):
    if request.user.is_authenticated:
        return redirect('home')

    mode = mode or request.GET.get('mode', 'login')
    if mode not in ('login', 'signup'):
        mode = 'login'

    login_form = LoginForm()
    register_form = RegisterForm()

    if request.method == 'POST':
        mode = request.POST.get('mode', mode)

        if mode == 'signup':
            register_form = RegisterForm(request.POST)
            if register_form.is_valid():
                user = register_form.save()
                login(request, user)
                messages.success(
                    request,
                    f'Account created. Welcome, {user.first_name}!',
                )
                return redirect('home')
            messages.error(request, 'Please fix the errors below.')
        else:
            login_form = LoginForm(request, data=request.POST)
            if login_form.is_valid():
                login(request, login_form.get_user())
                messages.success(
                    request,
                    f'Welcome back, {login_form.get_user().username}!',
                )
                next_url = request.GET.get('next') or 'home'
                return redirect(next_url)
            messages.error(request, 'Invalid username or password.')
    else:
        if mode == 'signup':
            register_form = RegisterForm()

    return render(request, 'rental/auth.html', {
        'login_form': login_form,
        'register_form': register_form,
        'mode': mode,
    })


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')


# ============================================================
#   OTP based mobile authentication (JSON API)
# ============================================================

import json as _json

from django.contrib.auth import get_user_model
from django.views.decorators.csrf import ensure_csrf_cookie

User = get_user_model()


def _json_body(request):
    try:
        return _json.loads(request.body.decode('utf-8') or '{}')
    except (ValueError, UnicodeDecodeError):
        return {}


def _user_for_phone(phone_internal):
    profile = Profile.objects.filter(phone=phone_internal).first()
    return profile.user if profile else None


def _next_otp(phone_internal, purpose):
    """Latest still-usable OTP for this phone + purpose."""
    now = timezone.now()
    return PhoneOTP.objects.filter(
        phone=phone_internal,
        purpose=purpose,
        is_used=False,
        expires_at__gt=now,
    ).order_by('-created_at').first()


@require_POST
def api_otp_send(request):
    data = _json_body(request)
    raw_phone = data.get('phone', '').strip()
    purpose = data.get('purpose', 'login')
    if purpose not in ('login', 'signup'):
        purpose = 'login'

    try:
        phone = otp_service.normalise_phone(raw_phone)
    except ValueError as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)

    cooldown = otp_service.resend_cooldown_left(phone, purpose)
    if cooldown > 0:
        return JsonResponse({
            'ok': False,
            'error': f'Please wait {cooldown}s before requesting another OTP.',
            'cooldown': cooldown,
        }, status=429)

    record, otp = otp_service.create_otp_record(phone, purpose)
    status_message = otp_service.deliver_otp(record, otp)

    return JsonResponse({
        'ok': True,
        'phone_mask': f'+{phone[:2]}******{phone[-2:]}',
        'channel': record.channel,
        'delivered_sms': record.channel == 'sms',
        'otp': otp if record.channel != 'sms' else '',  # never expose via page when SMS used
        'message': status_message,
    })


@require_POST
def api_otp_verify(request):
    data = _json_body(request)
    raw_phone = data.get('phone', '').strip()
    purpose = data.get('purpose', 'login')
    otp_value = str(data.get('otp', '')).strip()

    if purpose not in ('login', 'signup'):
        purpose = 'login'

    try:
        phone = otp_service.normalise_phone(raw_phone)
    except ValueError as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)

    record = _next_otp(phone, purpose)
    if record is None:
        return JsonResponse({
            'ok': False,
            'error': 'OTP has expired. Please request a new one.',
        }, status=410)

    if record.attempts >= settings.OTP_MAX_ATTEMPTS:
        record.is_used = True
        record.save(update_fields=['is_used'])
        return JsonResponse({
            'ok': False,
            'error': 'Too many wrong attempts. Please request a new OTP.',
        }, status=429)

    if not otp_service.check_otp(otp_value, record.otp_code_hash):
        record.attempts += 1
        record.save(update_fields=['attempts'])
        return JsonResponse({
            'ok': False,
            'error': 'Incorrect OTP. Please try again.',
        }, status=400)

    if not record.is_verified:
        record.is_verified = True
        record.save(update_fields=['is_verified'])

    existing_user = _user_for_phone(phone)

    if existing_user is not None:
        # OTP login: consume the OTP and start the session.
        record.is_used = True
        record.save(update_fields=['is_used'])
        login(request, existing_user, backend='django.contrib.auth.backends.ModelBackend')

    return JsonResponse({
        'ok': True,
        'new_user': existing_user is None,
        'user': existing_user.get_username() if existing_user else None,
    })


@require_POST
def api_auth_signup(request):
    data = _json_body(request)
    raw_phone = data.get('phone', '').strip()

    try:
        phone = otp_service.normalise_phone(raw_phone)
    except ValueError as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)

    record = _next_otp(phone, 'signup')
    if record is None or not record.is_verified:
        return JsonResponse({
            'ok': False,
            'error': 'Please verify your OTP first.',
        }, status=400)

    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip()
    full_name = (data.get('full_name') or '').strip()
    password = data.get('password') or ''

    if not username or not password:
        return JsonResponse({
            'ok': False,
            'error': 'Username and password are required.',
        }, status=400)
    if not (6 <= len(password) <= 128):
        return JsonResponse({
            'ok': False,
            'error': 'Password must be between 6 and 128 characters.',
        }, status=400)

    if User.objects.filter(username=username).exists():
        return JsonResponse({
            'ok': False,
            'error': 'That username is already taken.',
        }, status=409)
    if email and User.objects.filter(email=email).exists():
        return JsonResponse({
            'ok': False,
            'error': 'An account with that email already exists.',
        }, status=409)
    if _user_for_phone(phone) is not None:
        return JsonResponse({
            'ok': False,
            'error': 'This phone number is already registered. Please sign in.',
        }, status=409)

    parts = full_name.split(' ', 1)
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=parts[0] if parts else '',
        last_name=parts[1] if len(parts) > 1 else '',
    )
    Profile.objects.create(user=user, phone=phone)

    # Consume the OTP so it cannot be reused for another account.
    PhoneOTP.objects.filter(pk=record.pk).update(is_used=True)

    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return JsonResponse({'ok': True, 'message': 'Account created. Welcome!', 'user': username})


# ============================================================
#   Email verification (JSON API)
#   + email-only signup
# ============================================================

EMAIL_PURPOSE = EmailCode.VERIFY


@require_POST
def api_email_send(request):
    data = _json_body(request)
    try:
        email = email_service.normalise_email(data.get('email', ''))
    except ValueError as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)

    cooldown = email_service.resend_cooldown_left(email, EMAIL_PURPOSE)
    if cooldown > 0:
        return JsonResponse({
            'ok': False,
            'error': f'Please wait {cooldown}s before requesting another code.',
            'cooldown': cooldown,
        }, status=429)

    record, code = email_service.create_code_record(email, EMAIL_PURPOSE)
    channel, message = email_service.deliver_code(record, code)

    return JsonResponse({
        'ok': True,
        'email_mask': email_service.mask_email(email),
        'channel': channel,
        'email_delivered': channel == 'smtp',
        'code': code if channel == 'console' else '',  # dev exposure only
        'message': message,
    })


@require_POST
def api_email_confirm(request):
    data = _json_body(request)
    try:
        email = email_service.normalise_email(data.get('email', ''))
    except ValueError as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)

    code_value = str(data.get('code', '')).strip()

    record = email_service.latest_usable_code(email, EMAIL_PURPOSE)
    if record is None:
        return JsonResponse({
            'ok': False,
            'error': 'Code has expired. Please request a new one.',
        }, status=410)

    if record.attempts >= settings.OTP_MAX_ATTEMPTS:
        record.is_used = True
        record.save(update_fields=['is_used'])
        return JsonResponse({
            'ok': False,
            'error': 'Too many wrong attempts. Please request a new code.',
        }, status=429)

    if not otp_service.check_otp(code_value, record.code_hash):
        record.attempts += 1
        record.save(update_fields=['attempts'])
        return JsonResponse({
            'ok': False,
            'error': 'Incorrect code. Please try again.',
        }, status=400)

    if not record.is_verified:
        record.is_verified = True
        record.save(update_fields=['is_verified'])

    existing = User.objects.filter(email=email).first()
    if existing is not None:
        # A verified email address is a valid way back into the account.
        record.is_used = True
        record.save(update_fields=['is_used'])
        profile, _ = Profile.objects.get_or_create(user=existing)
        if not profile.email_verified:
            profile.email_verified = True
            profile.save(update_fields=['email_verified'])
        login(request, existing, backend='django.contrib.auth.backends.ModelBackend')
        return JsonResponse({
            'ok': True,
            'logged_in': True,
            'new_user': False,
            'user': existing.get_username(),
        })

    return JsonResponse({
        'ok': True,
        'logged_in': False,
        'new_user': True,
        'email': email,
    })


@require_POST
def api_email_signup(request):
    data = _json_body(request)
    try:
        email = email_service.normalise_email(data.get('email', ''))
    except ValueError as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)

    # The address must have been verified (unconsumed verified code exists).
    verified = EmailCode.objects.filter(
        email=email,
        purpose=EMAIL_PURPOSE,
        is_verified=True,
        is_used=False,
        expires_at__gt=timezone.now(),
    ).exists()
    if not verified:
        return JsonResponse({
            'ok': False,
            'error': 'Please verify your email address first.',
        }, status=400)

    username = (data.get('username') or '').strip()
    full_name = (data.get('full_name') or '').strip()
    password = data.get('password') or ''

    if not username or not password:
        return JsonResponse({
            'ok': False,
            'error': 'Username and password are required.',
        }, status=400)
    if not (6 <= len(password) <= 128):
        return JsonResponse({
            'ok': False,
            'error': 'Password must be between 6 and 128 characters.',
        }, status=400)
    if User.objects.filter(username=username).exists():
        return JsonResponse({
            'ok': False,
            'error': 'That username is already taken.',
        }, status=409)
    if User.objects.filter(email=email).exists():
        return JsonResponse({
            'ok': False,
            'error': 'An account with that email already exists. Please sign in.',
        }, status=409)

    parts = full_name.split(None, 1)
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=parts[0] if parts else '',
        last_name=parts[1] if len(parts) > 1 else '',
    )
    Profile.objects.create(user=user, email_verified=True)

    # Consume every verified code so it cannot be reused for another account.
    EmailCode.objects.filter(
        email=email,
        purpose=EMAIL_PURPOSE,
        is_used=False,
    ).update(is_used=True)

    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return JsonResponse({'ok': True, 'message': 'Account created. Welcome!', 'user': username})


# ============================================================
#   Google account sign-in (JSON API)
# ============================================================

def _verify_google_id_token(id_token):
    """Validate a Google ID token via Google's tokeninfo endpoint.

    Returns the decoded claims (dict) or None on any failure. The token is
    checked for its audience (our client id), issuer and expiry.
    """
    import urllib.parse
    import urllib.request

    url = settings.GOOGLE_TOKENINFO_URL + '?' + urllib.parse.urlencode(
        {'id_token': id_token},
    )
    try:
        with urllib.request.urlopen(url, timeout=settings.FAST2SMS_TIMEOUT_SECONDS) as resp:
            claims = _json.loads(resp.read().decode('utf-8'))
    except Exception as exc:
        print(f'[GOOGLE] tokeninfo request failed: {exc}')
        return None

    if 'error' in claims or 'error_description' in claims:
        print(f'[GOOGLE] token rejected: {claims.get("error_description") or claims.get("error")}')
        return None

    client_id = settings.GOOGLE_OAUTH_CLIENT_ID
    if client_id and claims.get('aud') != client_id:
        print(f'[GOOGLE] audience mismatch (got {claims.get("aud")}, expected own client).')
        return None

    if claims.get('iss') not in ('accounts.google.com', 'https://accounts.google.com'):
        return None

    exp = claims.get('exp')
    if exp and int(exp) < timezone.now().timestamp():
        return None

    if not claims.get('sub'):
        return None

    return claims


def _google_create_user(email, name, google_sub, email_verified):
    import re as _re

    base = email.split('@')[0]
    username = _re.sub(r'[^\w]', '_', base) or 'user'
    if not username[0].isalpha():
        username = 'u_' + username
    username = username[:30]

    candidate = username
    suffix = 1
    while User.objects.filter(username=candidate).exists():
        chunk = str(suffix)
        candidate = username[:30 - len(chunk)] + chunk
        suffix += 1
    username = candidate

    parts = name.split(None, 1)
    user = User.objects.create_user(username=username, email=email, password=None)
    user.first_name = (parts[0] if parts else '') or base
    if len(parts) > 1:
        user.last_name = parts[1]
    user.save(update_fields=['first_name', 'last_name'])

    Profile.objects.create(
        user=user,
        email_verified=email_verified,
        google_sub=google_sub or None,
    )
    return user


@require_POST
def api_auth_google(request):
    data = _json_body(request)
    id_token = (data.get('id_token') or '').strip()
    if not id_token:
        return JsonResponse({'ok': False, 'error': 'Missing Google credential.'}, status=400)

    claims = _verify_google_id_token(id_token)
    if claims is None:
        return JsonResponse({
            'ok': False,
            'error': 'Google verification failed. Please try again.',
        }, status=400)

    email = (claims.get('email') or '').strip().lower()
    if not email:
        return JsonResponse({
            'ok': False,
            'error': 'Your Google account has no email address.',
        }, status=400)

    name = (claims.get('name') or '').strip()
    google_sub = claims.get('sub')
    email_verified = bool(claims.get('email_verified'))

    user = None

    # 1) An account previously linked to this Google identity.
    if google_sub:
        profile = Profile.objects.filter(google_sub=google_sub).select_related('user').first()
        if profile:
            user = profile.user

    # 2) An existing account with the same email address.
    if user is None:
        user = User.objects.filter(email=email).first()

    new_user = user is None
    if new_user:
        user = _google_create_user(email, name, google_sub, email_verified)

    profile, _ = Profile.objects.get_or_create(user=user)
    changed = False
    if google_sub and profile.google_sub != google_sub:
        profile.google_sub = google_sub
        changed = True
    if email_verified and not profile.email_verified:
        profile.email_verified = True
        changed = True
    if changed:
        profile.save()

    if user.email != email and (not user.email or email_verified):
        user.email = email
        user.save(update_fields=['email'])

    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return JsonResponse({
        'ok': True,
        'new_user': new_user,
        'user': user.get_username(),
        'name': name or user.first_name or user.username,
        'email': email,
        'email_verified': user.profile.email_verified,
    })


@ensure_csrf_cookie
def auth_page(request, mode=None):
    if request.user.is_authenticated:
        return redirect('home')

    mode = mode or request.GET.get('mode', 'login')
    if mode not in ('login', 'signup'):
        mode = 'login'

    return render(request, 'rental/auth.html', {
        'mode': mode,
        'otp_expiry': settings.OTP_EXPIRY_MINUTES,
        'google_client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
        'email_smtp': email_service.smtp_configured(),
        'default_from_email': settings.DEFAULT_FROM_EMAIL,
    })


# ============================================================
#   OTP inbox — in-house database management of OTP records
# ============================================================

from django.contrib.admin.views.decorators import staff_member_required


@staff_member_required
def otp_inbox(request):
    """Staff dashboard listing every OTP record stored in the database.

    Plaintext OTPs are never stored — only their hashes — so the dashboard
    can resend (which generates a fresh OTP shown in a Django message) and
    manage the lifecycle (mark used / delete), while raw OTPs are delivered
    in-app and to the server console.
    """
    if request.method == 'POST':
        action = request.POST.get('action', '')
        record = get_object_or_404(PhoneOTP, pk=request.POST.get('pk', 0))

        if action == 'delete':
            phone = record.phone
            record.delete()
            messages.info(request, f'OTP record for +{phone} deleted.')
        elif action == 'mark_used':
            record.is_used = True
            record.save(update_fields=['is_used'])
            messages.info(request, f'OTP for +{record.phone} marked as used.')
        elif action == 'resend':
            new_record, otp = otp_service.create_otp_record(
                record.phone, record.purpose,
            )
            note = otp_service.deliver_otp(new_record, otp)
            if new_record.channel == 'sms':
                messages.info(
                    request,
                    f'New OTP SMS sent to +{record.phone} (record #{new_record.pk}). {note}',
                )
            else:
                messages.info(
                    request,
                    f'New OTP for +{record.phone}: {otp} '
                    f'(record #{new_record.pk}, in-app). {note}',
                )
        else:
            messages.warning(request, 'Unknown action.')

        return redirect('otp_inbox')

    otps = PhoneOTP.objects.all()[:50]
    return render(request, 'rental/otp_inbox.html', {'otps': otps})


# ============================================================
#   Profile & KYC verification (photo / driving licence / Aadhaar)
# ============================================================

@login_required
def profile(request):
    verification, _ = UserVerification.objects.get_or_create(user=request.user)
    context = {
        'verification': verification,
        'my_vehicles': Vehicle.objects.filter(owner=request.user),
        'trips': Trip.objects.filter(
            models.Q(renter=request.user) | models.Q(owner=request.user),
        )[:10],
        'claims': Claim.objects.filter(claimant=request.user)[:10],
    }
    return render(request, 'rental/profile.html', context)


@login_required
def verification(request):
    record, _ = UserVerification.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = VerificationForm(request.POST, request.FILES, instance=record)
        if form.is_valid():
            form.instance.status = UserVerification.PENDING
            form.instance.reviewed_at = None
            form.instance.reviewed_by = None
            form.instance.review_note = ''
            form.save()
            messages.success(
                request,
                'Verification details submitted! An admin will review them.',
            )
            return redirect('profile')
        messages.error(request, 'Please fix the errors below.')
    else:
        form = VerificationForm(instance=record)

    return render(request, 'rental/verify.html', {
        'form': form,
        'record': record,
    })


# ============================================================
#   Trips & GPS live tracking
# ============================================================

def _can_see_trip(trip, user):
    return user.is_staff or trip.renter == user or trip.owner == user


@login_required
def start_trip(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    if request.user == vehicle.owner:
        messages.error(request, 'You own this vehicle — you cannot rent your own ride.')
        return redirect('vehicle_detail', pk=pk)

    active = Trip.objects.filter(
        vehicle=vehicle,
        status=Trip.ACTIVE,
    ).first()
    if active:
        messages.info(request, 'This vehicle already has an active trip.')
        return redirect('track_trip', pk=active.pk)

    if not vehicle.available:
        messages.error(request, 'This vehicle is not available right now.')
        return redirect('vehicle_detail', pk=pk)

    trip = Trip.objects.create(
        renter=request.user,
        owner=vehicle.owner,
        vehicle=vehicle,
    )
    vehicle.available = False
    vehicle.save(update_fields=['available'])
    messages.success(request, 'Trip started! Live GPS tracking is now on.')
    return redirect('track_trip', pk=trip.pk)


@login_required
def end_trip(request, pk):
    trip = get_object_or_404(Trip, pk=pk)

    if trip.owner != request.user and trip.renter != request.user and not request.user.is_staff:
        return redirect('home')

    if trip.is_active:
        trip.status = Trip.COMPLETED
        trip.end_at = timezone.now()
        trip.save(update_fields=['status', 'end_at'])
        trip.vehicle.available = True
        trip.vehicle.save(update_fields=['available'])
        messages.success(request, 'Trip completed. Thanks for riding with Rent&Go!')

    return redirect('track_trip', pk=trip.pk)


@login_required
def track_trip(request, pk):
    trip = get_object_or_404(
        Trip.objects.select_related('vehicle', 'renter', 'owner'),
        pk=pk,
    )

    if not _can_see_trip(trip, request.user):
        messages.error(request, 'You can only watch trips you are part of.')
        return redirect('home')

    latest = trip.updates.first()
    context = {
        'trip': trip,
        'vehicle': trip.vehicle,
        'latest': latest,
        'update_count': trip.updates.count(),
        'updates_url': '/api/trips/%d/updates/' % trip.pk,
        'report_url': '/api/location/update/',
    }
    return render(request, 'rental/track.html', context)


@login_required
def api_location_update(request):
    """Store one GPS ping (real geolocation or simulatulated demo move)."""
    data = _json_body(request)

    try:
        trip = Trip.objects.get(pk=int(data.get('trip', 0)))
    except (TypeError, ValueError, Trip.DoesNotExist):
        return JsonResponse({'ok': False, 'error': 'Unknown trip.'}, status=400)

    if not _can_see_trip(trip, request.user):
        return JsonResponse({'ok': False, 'error': 'Not allowed.'}, status=403)
    if not trip.is_active:
        return JsonResponse({'ok': False, 'error': 'Trip is not active.'}, status=400)

    try:
        lat = float(data.get('lat'))
        lng = float(data.get('lng'))
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'Invalid coordinates.'}, status=400)

    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        return JsonResponse({'ok': False, 'error': 'Coordinates out of range.'}, status=400)

    update = LocationUpdate.objects.create(
        trip=trip,
        vehicle=trip.vehicle,
        latitude=lat,
        longitude=lng,
        speed_kmh=float(data.get('speed', 0) or 0),
        heading=float(data.get('heading', 0) or 0),
        accuracy_m=float(data.get('accuracy', 0) or 0),
        source=data.get('source', 'gps') if data.get('source') in (
            'gps', 'simulated') else 'gps',
    )
    return JsonResponse({
        'ok': True,
        'count': trip.updates.count(),
        'recorded_at': update.created_at.isoformat(),
    })


def api_trip_updates(request, pk):
    trip = get_object_or_404(Trip, pk=pk)
    if request.user.is_anonymous or not _can_see_trip(trip, request.user):
        return JsonResponse({'ok': False, 'error': 'Not allowed.'}, status=403)

    limit = int(request.GET.get('limit', 100) or 100)
    updates = trip.updates.order_by('created_at')[:limit]
    return JsonResponse({
        'ok': True,
        'trip': trip.pk,
        'count': trip.updates.count(),
        'updates': [
            {
                'lat': u.latitude,
                'lng': u.longitude,
                'speed': u.speed_kmh,
                'heading': u.heading,
                'accuracy': u.accuracy_m,
                'source': u.source,
                'at': u.created_at.isoformat(),
            }
            for u in updates
        ],
    })


# ============================================================
#   Risk / claims + FIR verification
# ============================================================

@login_required
def claims(request):
    if request.user.is_staff:
        queryset = Claim.objects.all()
    else:
        queryset = Claim.objects.filter(claimant=request.user)
    return render(request, 'rental/claims.html', {
        'claims': queryset,
        'is_staff': request.user.is_staff,
    })


@login_required
def file_claim(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    trips = Trip.objects.filter(vehicle=vehicle, renter=request.user).order_by('-start_at')
    latest_trip = trips.first()

    if request.method == 'POST':
        form = ClaimForm(request.POST, request.FILES)
        if form.is_valid():
            claim = form.save(commit=False)
            claim.claimant = request.user
            claim.vehicle = vehicle
            claim.trip = latest_trip
            claim.save()
            messages.success(
                request,
                'Claim filed! Keep your FIR and documents handy — our risk '
                'team will verify whether it is genuine.',
            )
            return redirect('claim_detail', pk=claim.pk)
        messages.error(request, 'Please fix the errors below.')
    else:
        form = ClaimForm(
            initial={
                'incident_at': timezone.now().strftime('%Y-%m-%dT%H:%M'),
                'latitude': vehicle.latitude if vehicle.latitude else '',
                'longitude': vehicle.longitude if vehicle.longitude else '',
                'incident_location': vehicle.location,
            },
        )

    return render(request, 'rental/claim_form.html', {
        'form': form,
        'vehicle': vehicle,
        'active_trip': latest_trip if latest_trip and latest_trip.is_active else None,
    })


@login_required
def claim_detail(request, pk):
    claim = get_object_or_404(
        Claim.objects.select_related('vehicle', 'claimant', 'trip'),
        pk=pk,
    )
    if not (request.user.is_staff or claim.claimant == request.user):
        messages.error(request, 'You cannot view this claim.')
        return redirect('home')

    return render(request, 'rental/claim_detail.html', {
        'claim': claim,
        'reviewable': request.user.is_staff,
    })


from django.contrib.admin.views.decorators import staff_member_required


@staff_member_required
def review_claim(request, pk):
    claim = get_object_or_404(Claim, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action', '')
        note = (request.POST.get('decision_note', '') or '').strip()

        mapping = {
            'under_review': Claim.UNDER_REVIEW,
            'approve': Claim.APPROVED,
            'reject': Claim.REJECTED,
            'settle': Claim.SETTLED,
        }
        if action in mapping:
            new_status = mapping[action]
            if new_status != claim.status:
                claim.status = new_status
            claim.verified = (new_status in (Claim.APPROVED, Claim.SETTLED))
            claim.decision_note = note or claim.decision_note
            claim.decided_by = request.user
            claim.decided_at = timezone.now()
            claim.save()
            if claim.verified:
                messages.success(request, 'Claim marked as VERIFIED genuine ✓')
            else:
                messages.success(request, f'Claim moved to {claim.get_status_display()}.')
        else:
            messages.warning(request, 'Unknown action.')

    return redirect('claim_detail', pk=claim.pk)


def risk(request):
    return render(request, 'rental/risk.html')