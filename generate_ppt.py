"""Generate the Rent&Go startup pitch deck (Rent&Go_Startup_Pitch.pptx)."""
import os

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   'Rent&Go_Startup_Pitch.pptx')

NAVY = RGBColor(0x0F, 0x1B, 0x33)
NAVY2 = RGBColor(0x1B, 0x2A, 0x4A)
INK = RGBColor(0x1C, 0x23, 0x33)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT = RGBColor(0xF5, 0xF8, 0xFD)
MUTED = RGBColor(0x5A, 0x68, 0x80)
ACCENT = RGBColor(0xF5, 0x9E, 0x0B)
GREEN = RGBColor(0x16, 0xA3, 0x4A)
RED = RGBColor(0xDC, 0x26, 0x26)
BLUE = RGBColor(0x1D, 0x4E, 0xD8)
BORDER = RGBColor(0xE0, 0xE6, 0xF0)

FONT = 'Calibri'

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]
SW, SH = 13.333, 7.5


def slide():
    return prs.slides.add_slide(BLANK)


def rect(s, x, y, w, h, color, line=None, shape=MSO_SHAPE.RECTANGLE, radius=None):
    sp = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if radius is not None:
        try:
            sp.adjustments[0] = radius
        except Exception:
            pass
    sp.fill.solid()
    sp.fill.fore_color.rgb = color
    if line is None:
        sp.line.fill.background()
    else:
        sp.line.color.rgb = line
        sp.line.width = Pt(1)
    sp.shadow.inherit = False
    return sp


def text(s, x, y, w, h, lines, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
         space_after=6):
    if lines and isinstance(lines[0], tuple):
        lines = [lines]
    elif lines and isinstance(lines[0], str) and len(lines) == 4 \
            and isinstance(lines[1], (int, float)):
        lines = [[tuple(lines)]]
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Pt(2)
    tf.margin_top = tf.margin_bottom = Pt(2)
    first = True
    for line in lines:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.alignment = align
        p.space_after = Pt(space_after)
        if isinstance(line, tuple):
            line = [line]
        for t, size, bold, color in line:
            r = p.add_run()
            r.text = t
            r.font.name = FONT
            r.font.size = Pt(size)
            r.font.bold = bold
            r.font.color.rgb = color
    return tb


def note_run(num, title, body, color):
    return [(f'{num}. ', 15, True, color), (title, 15, True, INK),
            (f'  {body}', 12, False, MUTED)]


def header(s, title, kicker=None, accent=ACCENT):
    rect(s, 0, 0, SW, 0.9, NAVY)
    rect(s, 0, 0.9, SW, 0.05, accent)
    if kicker:
        text(s, 0.55, 0.18, 9, 0.4, [kicker, 11, True, accent])
    text(s, 0.55, 0.42, 11, 0.5, [title, 24, True, WHITE])
    rect(s, SW - 0.5, 0.28, 0.22, 0.22, accent, shape=MSO_SHAPE.OVAL)


def footer(s, n, total):
    text(s, 0.5, SH - 0.38, 4, 0.3, [(f'Rent&Go · {n}/{total}',
                                       9, False, MUTED)])


def bullet_list(s, x, y, w, h, items, color=INK, size=15, gap=10):
    lines = []
    for it in items:
        if isinstance(it, tuple):
            head, rest = it
            lines.append([('•  ', size, True, ACCENT), (head, size, True, color),
                          ('  ' + rest, size, False, MUTED)])
        else:
            lines.append([('•  ', size, True, ACCENT), (it, size, False, color)])
    return text(s, x, y, w, h, lines, space_after=gap)


# ---------------- Slide 1 : Title ----------------
s = slide()
rect(s, 0, 0, SW, SH, NAVY)
rect(s, 0, 0, SW, 0.18, ACCENT)
big = rect(s, 1.3, 2.7, 4.2, 1.1, NAVY2, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.5)
text(s, 1.55, 2.85, 8, 0.9, [('RENT&GO', 54, True, WHITE)])
text(s, 1.55, 3.75, 9, 0.5, [('Rent vehicles. Borrow vehicles. Trusted by everyone.',
                                20, False, RGBColor(0xC9, 0xD4, 0xE7))])
text(s, 1.55, 4.5, 10, 0.5,
     [('Turn idle vehicles into income · get any vehicle when you need it', 14, False, ACCENT)])
tags = ['RENT A VEHICLE', 'BORROW & EARN', 'KYC VERIFIED', 'INSURE & GO']
x = 1.55
for i, t in enumerate(tags):
    w = 2.7
    rect(s, x, 5.55, w, 0.55, NAVY2, line=RGBColor(0x2E, 0x41, 0x66),
         shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.5)
    text(s, x + 0.25, 5.68, w - 0.5, 0.3, [t, 13, True, WHITE],
         align=PP_ALIGN.CENTER)
    x += w + 0.2
text(s, 0, 6.9, SW, 0.4, [('www.rentandgo.in — your trusted vehicle marketplace',
                            12, False, MUTED)], align=PP_ALIGN.CENTER)

# ---------------- Slide 2 : The Idea ----------------
s = slide()
header(s, 'The Startup Idea', 'WHY RENT&GO?')
bullet_list(s, 0.7, 1.3, 5.7, 4.5, [
    ('Ownership is expensive', 'cars and bikes sit idle 90%+ of the time but keep pocketing money'),
    ('Travel is unpredictable', 'airports, trips and errands need a vehicle right now'),
    ('Sharing is risky', 'no proof of who the driver is, no insurance in a mishap'),
])
c2 = rect(s, 6.9, 1.25, 5.7, 0.6, GREEN, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.4)
text(s, 7.1, 1.38, 5.3, 0.4, [('Rent&Go makes it simple and safe', 16, True, WHITE)])
bullet_list(s, 6.9, 2.05, 5.7, 4.5, [
    ('Rent', 'find a verified nearby vehicle in minutes, book and go'),
    ('Borrow & earn', 'list your idle vehicle and earn whenever it is used'),
    ('Trusted', 'every user and vehicle is verified and insured end-to-end'),
], color=GREEN)
footer(s, 2, 11)

# ---------------- Slide 3 : Borrow workflow ----------------
s = slide()
header(s, 'How It Works', 'FLOW · 1  RENTING A VEHICLE')
steps = [
    ('1', 'Browse', 'search by city, type & price'),
    ('2', 'Pick', 'choose a verified vehicle'),
    ('3', 'Verify', 'upload ID · licence · photo'),
    ('4', 'Book & Pay', 'secure online payment + deposit'),
    ('5', 'Go & Return', 'pick up on time, return inspected'),
]
x = 0.6
ix = 0
for num, title, sub in steps:
    w = 2.35
    rect(s, x, 2.3, w, 2.5, LIGHT, line=BORDER, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12)
    rect(s, x + 0.75, 2.55, 0.85, 0.85, NAVY, shape=MSO_SHAPE.OVAL)
    text(s, x + 0.75, 2.72, 0.85, 0.5, [num, 24, True, WHITE], align=PP_ALIGN.CENTER)
    text(s, x + 0.2, 3.6, w - 0.4, 0.4, [title, 16, True, INK], align=PP_ALIGN.CENTER)
    text(s, x + 0.2, 4.0, w - 0.4, 0.7, [sub, 12, False, MUTED], align=PP_ALIGN.CENTER)
    if ix < len(steps) - 1:
        ar = rect(s, x + w - 0.12, 3.3, 0.5, 0.5, ACCENT, shape=MSO_SHAPE.RIGHT_ARROW)
    x += w + 0.16
    ix += 1
text(s, 0.7, 5.3, 12, 1.2, [
    [('Instant booking ', 14, True, INK),
     ('— OTP confirmation, live helper and a digital trip ticket.', 14, False, MUTED)],
    [('Flexible plans ', 14, True, INK),
     ('— hourly, daily and weekly rentals with fair pricing.', 14, False, MUTED)],
], space_after=8)
footer(s, 3, 11)

# ---------------- Slide 4 : Earn workflow ----------------
s = slide()
header(s, 'How It Works', 'FLOW · 2  BORROW & EARN AS AN OWNER')
steps = [
    ('1', 'List your vehicle', 'add photos, price, availability'),
    ('2', 'Get verified', 'RC + insurance + owner KYC'),
    ('3', 'Match with drivers', 'verified renters only'),
    ('4', 'Hand over & track', 'insurer + our team watch every ride'),
    ('5', 'Get paid', 'clear earnings after each trip'),
]
x = 0.6
ix = 0
for num, title, sub in steps:
    w = 2.35
    rect(s, x, 2.3, w, 2.5, LIGHT, line=BORDER, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12)
    rect(s, x + 0.75, 2.55, 0.85, 0.85, GREEN, shape=MSO_SHAPE.OVAL)
    text(s, x + 0.75, 2.72, 0.85, 0.5, [num, 24, True, WHITE], align=PP_ALIGN.CENTER)
    text(s, x + 0.2, 3.6, w - 0.4, 0.4, [title, 16, True, INK], align=PP_ALIGN.CENTER)
    text(s, x + 0.2, 4.0, w - 0.4, 0.7, [sub, 12, False, MUTED], align=PP_ALIGN.CENTER)
    if ix < len(steps) - 1:
        rect(s, x + w - 0.12, 3.3, 0.5, 0.5, ACCENT, shape=MSO_SHAPE.RIGHT_ARROW)
    x += w + 0.16
    ix += 1
text(s, 0.7, 5.35, 12, 1.2, [
    [('Zero maintenance worry ', 14, True, INK),
     ('— our partners service and insure the vehicle.', 14, False, MUTED)],
    [('You stay in control ', 14, True, INK),
     ('— approve every booking before it is confirmed.', 14, False, MUTED)],
], space_after=8)
footer(s, 4, 11)

# ---------------- Slide 5 : Trusted platform / KYC ----------------
s = slide()
header(s, 'A Trusted Platform', 'WHO IS BEHIND THE WHEEL?  (KYC)')
cards = [
    ('Aadhaar', 'identity verified securely', NAVY),
    ('Driving Licence', 'valid for the vehicle class', BLUE),
    ('Face & Photo', 'matches the documents', GREEN),
    ('Phone & Email', 'OTP + link verification', ACCENT),
]
x = 0.6
for title, sub, col in cards:
    w = 2.95
    rect(s, x, 1.45, w, 2.0, LIGHT, line=BORDER, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12)
    rect(s, x + 0.2, 1.7, 0.55, 0.13, col)
    text(s, x + 0.2, 1.95, w - 0.4, 0.5, [title, 17, True, INK])
    text(s, x + 0.2, 2.55, w - 0.4, 0.8, [sub, 12, False, MUTED])
    x += w + 0.18
req = rect(s, 0.6, 3.85, 12.1, 2.6, NAVY, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.1)
text(s, 1.0, 4.15, 11, 0.5, [('What we check before a ride', 18, True, ACCENT)])
bullet_list(s, 1.0, 4.75, 11.3, 1.6, [
    ('Borrower', 'Aadhaar + driving licence + live photo — validated before the first ride'),
    ('Owner', 'owner KYC + RC book + valid insurance policy'),
    ('Booking', 're-verified every booking; lock/unlock only for the verified driver'),
], color=WHITE)
footer(s, 5, 11)

# ---------------- Slide 6 : Vehicle verification ----------------
s = slide()
header(s, 'Vehicle Verification', 'EVERY VEHICLE IS CHECKED')
checks = [
    ('RC book', 'registration & ownership verified'),
    ('Insurance', 'valid third-party + own-damage cover'),
    ('Condition photos', 'all four sides + odometer recorded'),
    ('Smart lock', 'only the booked driver can unlock'),
]
x = 0.6
for title, sub in checks:
    w = 2.95
    rect(s, x, 1.5, w, 1.9, LIGHT, line=BORDER, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12)
    text(s, x + 0.25, 1.75, w - 0.5, 0.5, [('✓  ', 15, True, GREEN), (title, 16, True, INK)])
    text(s, x + 0.25, 2.3, w - 0.5, 1.0, [sub, 12, False, MUTED])
    x += w + 0.18
text(s, 0.7, 3.75, 12, 0.4, [('On pickup', 16, True, NAVY)])
bullet_list(s, 0.7, 4.25, 12, 1.6, [
    ('Time-stamped handover with photo proof of damage-free / existing damage state'),
    ('Fuel level, odometer and cleanliness recorded on both sides'),
    ('A digital trip ticket keeps both borrower and owner on the same page'),
])
footer(s, 6, 11)

# ---------------- Slide 7 : Accident system ----------------
s = slide()
header(s, 'If Something Goes Wrong', 'ACCIDENT HANDLING SYSTEM', accent=RED)
steps = [
    ('1', 'Safety first', 'move to safety · call 112 · tap the red SOS in the app'),
    ('2', 'Report in-app', 'car model, plate, location, photos — posted in seconds'),
    ('3', 'Verification', 'we confirm Aadhaar, driving licence and the active rental'),
    ('4', 'Insurance claim', 'our insurance partner opens a case with the vehicle & policy details'),
    ('5', 'Support & resolve', 'documents collected, claims tracked, deposit and repair handled'),
]
y = 1.4
for num, title, sub in steps:
    rect(s, 1.1, y, 0.95, 0.95, RED, shape=MSO_SHAPE.OVAL)
    text(s, 1.1, y + 0.25, 0.95, 0.5, [num, 22, True, WHITE], align=PP_ALIGN.CENTER)
    rect(s, 2.35, y - 0.08, 9.6, 1.05, LIGHT, line=BORDER, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.2)
    text(s, 2.7, y + 0.14, 9, 0.6,
         [[(title, 16, True, INK), ('   ' + sub, 13, False, MUTED)]])
    y += 1.16
text(s, 1.1, 6.9, 11, 0.4,
     [('All identity, licence, vehicle and insurance details stay private and are shared only for your claim.',
        11, False, MUTED)], align=PP_ALIGN.CENTER)
footer(s, 7, 11)

# ---------------- Slide 8 : Insurance & safety ----------------
s = slide()
header(s, 'Insurance & Safety', 'RIDE WITH PEACE OF MIND')
box = [
    ('Coverage', 'every ride includes third-party and own-damage insurance from our partner insurer'),
    ('Security deposit', 'refundable — released after a clean, damage-free return'),
    ('Assistance', '24 x 7 helpline, roadside support and emergency contacts on every trip'),
    ('Fair ratings', 'borrowers and owners rate each trip; repeat offenders are removed'),
]
y = 1.5
for title, body in box:
    rect(s, 0.7, y, 0.14, 1.05, GREEN)
    text(s, 1.05, y, 11.6, 1.05,
         [[(title, 16, True, INK)], [(body, 13, False, MUTED)]], space_after=3)
    y += 1.35
footer(s, 8, 11)

# ---------------- Slide 9 : Tech ----------------
s = slide()
header(s, 'Built on Solid Technology', 'TECHNOLOGY')
bullet_list(s, 0.7, 1.4, 6, 4.6, [
    ('Django web app', 'fast, secure and scalable core'),
    ('MySQL database', 'users, bookings, vehicles, claims'),
    ('Phone OTP sign-in', 'Fast2SMS verification in seconds'),
    ('Email verification', 'confirms the account safely'),
    ('Google sign-in', 'one-click social login'),
])
tech = [
    ('KYC & Docs', 'Aadhaar + licence + RC + insurance stored securely'),
    ('Booking engine', 'search, lock, payment and trip tickets'),
    ('Accident module', 'report, verify, insure and resolve claims'),
]
y = 1.4
for t, b in tech:
    rect(s, 7.2, y, 5.4, 1.35, LIGHT, line=BORDER, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.15)
    text(s, 7.5, y + 0.15, 4.9, 1.1,
         [[(t, 15, True, BLUE)], [(b, 12, False, MUTED)]], space_after=3)
    y += 1.55
footer(s, 9, 11)

# ---------------- Slide 10 : Roadmap ----------------
s = slide()
header(s, 'What Comes Next', 'ROADMAP')
roads = [
    ('Phase 1 · Now', 'rental marketplace live with OTP/email/Google login, KYC and accident handling'),
    ('Phase 2 · Soon', 'live GPS tracking + smart locks for safe handover'),
    ('Phase 3 · Next', 'AI damage detection from photos at pickup and return'),
    ('Phase 4 · Future', 'partner fleets, long-term leases and rewards for top users'),
]
y = 1.5
for phase, body in roads:
    rect(s, 0.7, y, 2.4, 1.05, NAVY, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.2)
    text(s, 0.85, y + 0.35, 2.1, 0.5, [phase, 14, True, ACCENT], align=PP_ALIGN.CENTER)
    rect(s, 3.35, y, 9.3, 1.05, LIGHT, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.2)
    text(s, 3.6, y + 0.15, 8.8, 0.8, [body, 13, False, INK])
    y += 1.25
footer(s, 10, 11)

# ---------------- Slide 11 : Thank you ----------------
s = slide()
rect(s, 0, 0, SW, SH, NAVY)
rect(s, 0, 0, SW, 0.18, ACCENT)
text(s, 0, 2.4, SW, 1.0, [('Thank You', 52, True, WHITE)], align=PP_ALIGN.CENTER)
text(s, 0, 3.5, SW, 0.6, [('Rent a vehicle · Borrow & earn · Ride safe', 20, False, RGBColor(0xC9, 0xD4, 0xE7))],
     align=PP_ALIGN.CENTER)
text(s, 0, 4.6, SW, 0.5, [('KYC verified drivers · verified vehicles · insured every ride',
                            14, False, ACCENT)], align=PP_ALIGN.CENTER)
text(s, 0, 5.9, SW, 0.5, [('hello@rentandgo.in   |   www.rentandgo.in',
                            14, True, WHITE)], align=PP_ALIGN.CENTER)

prs.save(OUT)
print('saved:', OUT, f'({os.path.getsize(OUT):,} bytes, {len(prs.slides._sldIdLst)} slides)')