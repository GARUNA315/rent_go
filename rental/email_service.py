"""Email address verification: code generation + delivery + DB check.

Delivery is pluggable, mirroring the mobile OTP service:

* SMTP — used automatically the moment EMAIL_HOST is configured (env var or
  .env file). The code is emailed for real and never shown in the browser.
* Console — development fallback: the code is printed to the server console
  and (because SMTP is not configured) also returned in the API response so
  the flow can be completed on the auth page.

Only the hash of the code is stored in the EmailCode table; every code is
consumed after it has been used.
"""

import re

from django.conf import settings
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.utils import timezone

from .otp_service import check_otp, generate_otp, hash_otp

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def normalise_email(raw):
    """Lowercase + strip; raises ValueError for clearly invalid addresses."""
    email = str(raw or '').strip().lower()
    if not email or not _EMAIL_RE.match(email):
        raise ValueError('Please enter a valid email address.')
    try:
        validate_email(email)
    except Exception:
        raise ValueError('Please enter a valid email address.')
    return email


def mask_email(email):
    """Return a masked view like a******x@example.com."""
    local, _, domain = email.partition('@')
    if len(local) <= 2:
        masked_local = local[0] + '*' * (len(local) - 1)
    else:
        masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
    return masked_local + '@' + domain


def create_code_record(email, purpose):
    """Generate + persist a fresh verification code and return (record, code)."""
    from .models import EmailCode

    code = generate_otp()

    # Any earlier unconsumed code for the same email + purpose is superseded
    # by a new request, so an old code can never be replayed.
    EmailCode.objects.filter(
        email=email,
        purpose=purpose,
        is_used=False,
    ).update(is_used=True)

    record = EmailCode.objects.create(
        email=email,
        purpose=purpose,
        code_hash=hash_otp(code),
        expires_at=timezone.now() + timezone.timedelta(minutes=settings.OTP_EXPIRY_MINUTES),
        last_sent_at=timezone.now(),
    )
    return record, code


def smtp_configured():
    return bool(
        settings.EMAIL_HOST
        and settings.EMAIL_HOST.upper() not in ('', 'PASTE_YOUR_SMTP_HOST_HERE')
    )


def deliver_code(record, code):
    """Send the code through the best available channel.

    The operator always sees it in the console; the requester sees it in the
    API response only in development (console channel), not when real SMTP is
    configured.
    """
    from .models import EmailCode

    subject = f'Rent&Go — your verification code is {code}'
    body = (
        f'Hello,\n\n'
        f'Your Rent&Go email verification code is: {code}\n\n'
        f'The code is valid for {settings.OTP_EXPIRY_MINUTES} minutes and '
        f'can be used only once.\n\n'
        f'If you did not request this, you can safely ignore this email.\n\n'
        f'— The Rent&Go team'
    )

    if smtp_configured():
        try:
            send_mail(
                subject,
                body,
                settings.DEFAULT_FROM_EMAIL,
                [record.email],
                fail_silently=False,
            )
            record.channel = EmailCode.SMTP
            record.save(update_fields=['channel'])
            print(f'[EMAIL] Verification code {code} emailed to {record.email}.')
            return record.channel, 'Verification code sent by email.'
        except Exception as exc:
            print(f'[EMAIL] Could not send email to {record.email}: {exc}')

    record.channel = EmailCode.CONSOLE
    record.save(update_fields=['channel'])
    print(f'[EMAIL] Verification code {code} for {record.email} (console, no SMTP).')
    return record.channel, 'No SMTP configured — code shown on screen instead.'


def resend_cooldown_left(email, purpose):
    """Seconds until the same email+purpose may request another code."""
    from .models import EmailCode

    latest = EmailCode.objects.filter(
        email=email,
        purpose=purpose,
    ).order_by('-last_sent_at').first()

    if not latest or not latest.last_sent_at:
        return 0

    elapsed = (timezone.now() - latest.last_sent_at).total_seconds()
    remaining = settings.OTP_RESEND_COOLDOWN_SECONDS - elapsed
    return max(0, int(remaining))


def latest_usable_code(email, purpose):
    """The newest unconsumed, unexpired code for this address + purpose."""
    from .models import EmailCode

    return EmailCode.objects.filter(
        email=email,
        purpose=purpose,
        is_used=False,
        expires_at__gt=timezone.now(),
    ).order_by('-created_at').first()


def email_already_verified(email):
    """True when an account with this verified address already exists."""
    from django.contrib.auth import get_user_model
    return get_user_model().objects.filter(email=email).exists()