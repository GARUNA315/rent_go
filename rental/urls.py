from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('vehicles/', views.vehicles, name='vehicles'),
    path('vehicles/<int:pk>/', views.vehicle_detail, name='vehicle_detail'),
    path('add-vehicle/', views.add_vehicle, name='add_vehicle'),
    path('auth/', views.auth_page, name='auth'),
    path('auth.html', views.auth_page, name='auth_html'),
    path('login/', views.auth_page, {'mode': 'login'}, name='login'),
    path('register/', views.auth_page, {'mode': 'signup'}, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('otp-inbox/', views.otp_inbox, name='otp_inbox'),

    # Profile / verification
    path('profile/', views.profile, name='profile'),
    path('profile/verify/', views.verification, name='verify'),

    # Trips & GPS tracking
    path('vehicles/<int:pk>/start-trip/', views.start_trip, name='start_trip'),
    path('trips/<int:pk>/end-trip/', views.end_trip, name='end_trip'),
    path('trips/<int:pk>/track/', views.track_trip, name='track_trip'),
    path('api/location/update/', views.api_location_update, name='api_location_update'),
    path('api/trips/<int:pk>/updates/', views.api_trip_updates, name='api_trip_updates'),

    # Claims & FIR verification
    path('claims/', views.claims, name='claims'),
    path('vehicles/<int:pk>/claims/new/', views.file_claim, name='file_claim'),
    path('claims/<int:pk>/', views.claim_detail, name='claim_detail'),
    path('claims/<int:pk>/review/', views.review_claim, name='review_claim'),

    # Risk & terms
    path('risk/', views.risk, name='risk'),

    # OTP / mobile verification API
    path('api/otp/send/', views.api_otp_send, name='api_otp_send'),
    path('api/otp/verify/', views.api_otp_verify, name='api_otp_verify'),
    path('api/auth/signup/', views.api_auth_signup, name='api_auth_signup'),

    # Email verification API
    path('api/email/verify/send/', views.api_email_send, name='api_email_send'),
    path('api/email/verify/confirm/', views.api_email_confirm, name='api_email_confirm'),
    path('api/auth/email-signup/', views.api_email_signup, name='api_email_signup'),

    # Google sign-in API
    path('api/auth/google/', views.api_auth_google, name='api_auth_google'),
]