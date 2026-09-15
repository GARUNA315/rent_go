from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User

from .models import Claim, Vehicle, UserVerification


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=50, required=True)
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('first_name', 'username', 'email',
                  'password1', 'password2')


class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(
        attrs={'placeholder': 'Username or email'}))
    password = forms.CharField(widget=forms.PasswordInput(
        attrs={'placeholder': 'Password'}))


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = (
            'name', 'brand', 'vehicle_type', 'year',
            'price_per_day', 'location', 'latitude',
            'longitude', 'image', 'photo', 'description', 'available',
            'registration_number', 'rc_image',
            'insurance_number', 'insurance_provider',
            'insurance_valid_until', 'insurance_image',
        )
        widgets = {
            'vehicle_type': forms.Select(choices=Vehicle.VEHICLE_TYPES),
            'year': forms.NumberInput(attrs={'min': 1990, 'max': 2026}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'insurance_valid_until': forms.DateInput(
                attrs={'type': 'date'},
                format='%Y-%m-%d',
            ),
        }

    def clean_price_per_day(self):
        price = self.cleaned_data['price_per_day']
        if price <= 0:
            raise forms.ValidationError('Price must be greater than zero.')
        return price

    def clean_registration_number(self):
        value = (self.cleaned_data.get('registration_number') or '').strip()
        return value.upper()


class VerificationForm(forms.ModelForm):
    aadhaar_no = forms.CharField(
        max_length=14,
        widget=forms.TextInput(
            attrs={'placeholder': '12-digit Aadhaar number', 'maxlength': 14}),
        help_text='12 digits. Only the last 4 are ever shown publicly.',
    )

    class Meta:
        model = UserVerification
        fields = (
            'photo', 'driving_license_no', 'driving_license_image',
            'aadhaar_no', 'aadhaar_image',
        )
        widgets = {
            'driving_license_no': forms.TextInput(
                attrs={'placeholder': 'e.g. MH0120211234567'}),
        }

    def clean_driving_license_no(self):
        value = (self.cleaned_data.get('driving_license_no') or '').strip()
        if not value:
            raise forms.ValidationError('Driving licence number is required.')
        if len(value) < 8:
            raise forms.ValidationError('That driving licence number looks too short.')
        return value

    def clean_aadhaar_no(self):
        value = (self.cleaned_data.get('aadhaar_no') or '').strip()
        digits = ''.join(ch for ch in value if ch.isdigit())
        if not digits:
            raise forms.ValidationError('Aadhaar number is required.')
        if len(digits) != 12:
            raise forms.ValidationError('Aadhaar must be exactly 12 digits.')
        return digits


class ClaimForm(forms.ModelForm):
    class Meta:
        model = Claim
        fields = (
            'kind', 'description', 'incident_at',
            'incident_location', 'latitude', 'longitude',
            'damage_estimate', 'photo', 'photo2',
            'fir_number', 'fir_station', 'fir_image',
        )
        widgets = {
            'kind': forms.Select(),
            'description': forms.Textarea(attrs={'rows': 4}),
            'incident_at': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
            'incident_location': forms.TextInput(),
            'damage_estimate': forms.NumberInput(attrs={'min': 0}),
        }

    def clean_damage_estimate(self):
        value = self.cleaned_data.get('damage_estimate')
        if value is not None and value < 0:
            raise forms.ValidationError('Estimate must be zero or greater.')
        return value

    def clean(self):
        cleaned = super().clean()
        fir = (cleaned.get('fir_number') or '').strip()
        station = (cleaned.get('fir_station') or '').strip()
        if fir and not station:
            self.add_error(
                'fir_station',
                'Please add the police station name along with the FIR number.',
            )
        return cleaned