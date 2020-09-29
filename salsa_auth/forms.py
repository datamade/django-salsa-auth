from django import forms
from django.core.exceptions import ValidationError


class BootstrapMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'


class HiddenFieldForm(forms.Form):
    address = forms.CharField(widget=forms.HiddenInput(), required=False)

    def clean_address(self):
        if self.cleaned_data.get('address', None):
            raise ValidationError('Invalid value for hidden field')


class SignUpForm(BootstrapMixin, HiddenFieldForm):
    email = forms.EmailField(label='Email')
    first_name = forms.CharField(label='First name')
    last_name = forms.CharField(label='Last name')
    zip_code = forms.CharField(label='Zip code')


class LoginForm(BootstrapMixin, HiddenFieldForm):
    email = forms.EmailField(label='Email')
