from uuid import uuid4

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.views.generic import FormView, TemplateView

from salsa_auth.forms import SignUpForm, LoginForm
from salsa_auth.models import UserZipCode
from salsa_auth.salsa import client as salsa_client
from salsa_auth.tokens import account_activation_token


class JSONFormResponseMixin:
    def form_valid(self, form):
        context = self.get_context_data(form=form)
        return self.render_to_response(context)

    def form_invalid(self, form):
        context = self.get_context_data(form=form)
        return self.render_to_response(context)

    def render_to_response(self, context, **kwargs):
        response = {}

        errors = context['form'].errors

        if errors:
            response['redirect_url'] = None
            response['errors'] = errors
        else:
            response['redirect_url'] = getattr(self, 'redirect_url', self.request.POST.get('next'))

        return JsonResponse(response)


class SignUpForm(JSONFormResponseMixin, FormView):
    form_class = SignUpForm
    template_name = 'signup.html'

    def form_valid(self, form):
        user = self._make_user(form.cleaned_data)

        # TO-DO: Potentially intercept SMTP error for undeliverable mail here
        self._send_verification_email(user)

        message =  'Please check your email for a verification code.'

        if message not in [m.message for m in messages.get_messages(self.request)]:
            messages.add_message(self.request, messages.INFO, message)

        return super().form_valid(form)

    def _make_user(self, form_data):
        zip_code = form_data.pop('zip_code')

        user = User.objects.create(**form_data, username=str(uuid4()).split('-')[0])
        user.set_unusable_password()
        user.save()

        user_zip = UserZipCode.objects.create(user=user, zip_code=zip_code)

        return user

    def _send_verification_email(self, user):
        current_site = get_current_site(self.request)
        email_subject = 'Activate Your Account'
        message = render_to_string('emails/activate_account.html', {
            'user': user,
            'domain': current_site.domain,
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': account_activation_token.make_token(user),
        })
        send_mail(email_subject, message, 'testing@datamade.us', [user.email])


class LoginForm(JSONFormResponseMixin, FormView):
    form_class = LoginForm
    template_name = 'login.html'
    redirect_url = '/salsa/authenticate'

    def post(self, *args, **kwargs):
        form = self.get_form()

        if form.is_valid():
            user = salsa_client.get_supporter(form.cleaned_data['email'])

            if not user:
                error_message = (
                    '<strong>{email}</strong> is not subscribed to the BGA mailing list. Please '
                    '<a href="javascript://" class="toggle-login-signup" data-parent_modal="loginModal">sign up</a> '
                    'to access this tool.'
                )
                form.errors['email'] = [error_message.format(email=form.cleaned_data['email'])]
                return self.form_invalid(form)

            return self.form_valid(form)

        return self.form_invalid(form)


class VerifyEmail(TemplateView):
    def get(self, request, uidb64, token):
        '''
        https://simpleisbetterthancomplex.com/tutorial/2016/08/24/how-to-create-one-time-link.html
        '''
        try:
            uid = force_text(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        link_valid = user is not None and account_activation_token.check_token(user, token)

        if link_valid:
            salsa_client.put_supporter(user)
            return redirect('salsa_auth:authenticate')

        else:
            # TO-DO: Add a message
            return redirect('salsa_auth:signup')


class Authenticate(TemplateView):
    template_name = 'authenticate.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update({
            'cookie_name': settings.SALSA_AUTH_COOKIE_NAME,
            'cookie_domain': settings.SALSA_AUTH_COOKIE_DOMAIN,
            'redirect_location': settings.SALSA_AUTH_REDIRECT_LOCATION,
        })
        return context


class Logout(TemplateView):
    pass
