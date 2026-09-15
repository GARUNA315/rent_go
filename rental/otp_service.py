"""OTP generation, pluggable delivery, and DB-backed verification.

Delivery notes on the available channels:

* SMS (Fast2SMS) — used automatically the moment FAST2SMS_API_KEY is set
  (env var or .env file). Numbers are delivered via the Fast2SMS OTP route.
* In-app — OTP shown on the page + printed to the console. Used as a
  fallback when no SMS key is configured or when SMS delivery fails.

Every OTP is generated here, only its hash is stored in the PhoneOTP table,
and it is consumed after use. Verification is constant-time against the DB.
"""

import json
import re
import secrets
import urllib.parse
import urllib.request

from django.conf import settings
from django.utils import timezone

OTP_LENGTH = 6

_PHONE_RE = re.compile(r'^[6-9]\d{9}$')


def normalise_phone(raw):
    """Return '91' + 10-digit Indian mobile, or raise ValueError."""
    digits = re.sub(r'\D', '', str(raw or ''))
    if digits.startswith('91') and len(digits) == 12:
        digits = digits[2:]
    elif digits.startswith('0') and len(digits) == 11:
        digits = digits[1:]
    if not _PHONE_RE.match(digits):
        raise ValueError('Please enter a valid 10-digit Indian mobile number.')
    return '91' + digits


def local_phone(phone):
    """Strip the country code → the 10-digit number used by Fast2SMS."""
    return phone[-10:] if phone.startswith('91') else phone


def generate_otp():
    """Return a random numeric OTP (left-padded with zeros)."""
    return f'{secrets.randbelow(10 ** OTP_LENGTH):0{OTP_LENGTH}d}'


def hash_otp(otp):
    """Store only a hash of the OTP, never the plain value."""
    from django.contrib.auth.hashers import make_password
    return make_password(otp)


def check_otp(otp, otp_hash):
    """Constant-time comparison of the provided OTP against its hash."""
    from django.contrib.auth.hashers import check_password
    return check_password(otp, otp_hash)


def create_otp_record(phone_internal, purpose):
    """Generate + persist a fresh OTP and return (record, otp)."""
    from django.utils import timezone as tz

    from .models import PhoneOTP

    otp = generate_otp()

    # Invalidate any earlier, unconsumed OTP for the same phone + purpose so a
    # new request always supersedes the previous one.
    PhoneOTP.objects.filter(
        phone=phone_internal,
        purpose=purpose,
        is_used=False,
    ).update(is_used=True)

    record = PhoneOTP.objects.create(
        phone=phone_internal,
        purpose=purpose,
        otp_code_hash=hash_otp(otp),
        expires_at=tz.now() + tz.timedelta(minutes=settings.OTP_EXPIRY_MINUTES),
        last_sent_at=tz.now(),
    )
    return record, otp


# ---------------------------------------------------------------------------
#   Delivery plug-ins
# ---------------------------------------------------------------------------

def send_otp_sms(phone_internal, otp):
    """Deliver an OTP over SMS through Fast2SMS (bulkV2 OTP route).

    The API key goes in the request headers, as Fast2SMS expects; the OTP
    route uses their fixed sender id, so no sender_id is sent.

    Returns (delivered, message).
    """
    payload = urllib.parse.urlencode({
        'route': 'otp',
        'variables_values': otp,
        'numbers': local_phone(phone_internal),
        'flash': '0',
    }).encode('utf-8')

    request = urllib.request.Request(
        'https://www.fast2sms.com/dev/bulkV2',
        data=payload,
        headers={
            'authorization': settings.FAST2SMS_API_KEY,
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': '*/*',
        },
        method='POST',
    )

    try:
        with urllib.request.urlopen(request, timeout=settings.FAST2SMS_TIMEOUT_SECONDS) as response:
            body = response.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', 'replace')[:300] if exc.fp else str(exc)
        print(f'[OTP] Fast2SMS HTTP {exc.code}: {detail}')
        return False, f'Fast2SMS HTTP {exc.code}: {detail}'
    except Exception as exc:
        print(f'[OTP] Fast2SMS request failed: {exc}')
        return False, f'Fast2SMS request failed: {exc}'

    try:
        data = json.loads(body)
        if data.get('return'):
            return True, 'OTP sent by SMS.'
        message = data.get('message', body)[:200]
        print(f'[OTP] Fast2SMS rejected: {message}')
        return False, f'Fast2SMS rejected: {message}'
    except ValueError:
        return False, f'Fast2SMS returned an unexpected response: {body[:120]}'


def deliver_otp(record, otp):
    """Deliver the OTP through the best available channel.

    The server operator always sees it in the console. The sender sees it
    on the page only when in-app delivery is used.
    """
    from .models import PhoneOTP

    print(f'[OTP] {record.purpose.upper()} for +{record.phone}: {otp}')

    # 1) Real SMS whenever a real Fast2SMS key is configured.
    api_key = settings.FAST2SMS_API_KEY
    placeholder = 'PASTE_YOUR_API_KEY_HERE'
    if api_key and api_key != placeholder:
        delivered, message = send_otp_sms(record.phone, otp)
        record.channel = PhoneOTP.SMS if delivered else PhoneOTP.INAPP
        record.save(update_fields=['channel'])
        if delivered:
            return message
        return message + ' — showing OTP in-app instead.'

    # 2) In-app fallback (no SMS configured).
    record.channel = PhoneOTP.INAPP
    record.save(update_fields=['channel'])
    return 'No SMS key configured - OTP shown in-app.'


def resend_cooldown_left(phone_internal, purpose):
    """Seconds until the same phone+purpose may request another OTP."""
    from .models import PhoneOTP

    latest = PhoneOTP.objects.filter(
        phone=phone_internal,
        purpose=purpose,
    ).order_by('-last_sent_at').first()

    if not latest or not latest.last_sent_at:
        return 0

    elapsed = (timezone.now() - latest.last_sent_at).total_seconds()
    remaining = settings.OTP_RESEND_COOLDOWN_SECONDS - elapsed
    return max(0, int(remaining))