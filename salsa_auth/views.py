import datetime
from uuid import uuid4

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.views.generic import FormView, RedirectView

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
            response['redirect_url'] = getattr(self, 'redirect_url', self.request.POST['next'])

        return JsonResponse(response)


class SignUpForm(JSONFormResponseMixin, FormView):
    form_class = SignUpForm
    template_name = 'signup.html'

    def form_valid(self, form):
        print(form.cleaned_data, flush=True)

        email = form.cleaned_data['email']

        # If the email already exists in Salsa, re-verification is not required.
        # Authenticate the user.
        salsa_user = salsa_client.get_supporter(email)

        if salsa_user:
            # Sometimes the user's first name is not in Salsa.
            welcome_message = 'Welcome back, {}!'.format(salsa_user.get('firstName', email))

            messages.add_message(self.request,
                                 messages.INFO,
                                 welcome_message,
                                 extra_tags='font-weight-bold')

            self.redirect_url = reverse('salsa_auth:authenticate')

        else:
            pending_user = User.objects.filter(email=email).order_by('date_joined').first()

            if not pending_user:
                new_user = self._make_user(form.cleaned_data)

                self._send_verification_email(new_user)

                message_title = 'Thanks for signing up!'
                message_body = '<p>Please check your email for an activation link.</p>'

            else:
                message_title = 'Verify your email address'
                message_body = '<p>We sent an activation link to <strong>{0}</strong> on <strong>{1}</strong>.</p>'.format(
                    pending_user.email,
                    datetime.datetime.strftime(pending_user.date_joined, '%B %d, %Y')
                )

            message_body += (
                "<p>If you don't receive an email from <strong>no-reply@bettergov.org</strong> "
                'shortly, please be sure to check your email’s spam folder. '
                'If you continue encountering problems accessing the database, '
                'please contact our <a href="https://www.bettergov.org/team/jared-rutecki" target="_blank">Data Coordinator</a>.'
            )

            messages.add_message(self.request, messages.INFO, message_title, extra_tags='font-weight-bold')
            messages.add_message(self.request, messages.INFO, message_body)

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

        uid = urlsafe_base64_encode(force_bytes(user.pk))

        # uid will be a bytestring in Django < 2.2. Cast it to a string before
        # rendering it into the email template.
        if isinstance(uid, (bytes, bytearray)):
            uid = uid.decode('utf-8')

        message = render_to_string('emails/activate_account.html', {
            'user': user,
            'domain': current_site.domain,
            'uid': uid,
            'token': account_activation_token.make_token(user),
        })
        send_mail(email_subject,
                  message,
                  getattr(settings, 'DEFAULT_FROM_EMAIL', 'testing@datamade.us'),
                  [user.email])


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

            try:
                greeting_name = user['firstName']
            except KeyError:
                greeting_name = form.cleaned_data['email']

            messages.add_message(self.request,
                                 messages.INFO,
                                 'Welcome back, {}!'.format(greeting_name),
                                 extra_tags='font-weight-bold')

            return self.form_valid(form)

        return self.form_invalid(form)


class VerifyEmail(RedirectView):
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

            messages.add_message(self.request,
                                 messages.INFO,
                                 'Welcome back, {}!'.format(user.first_name),
                                 extra_tags='font-weight-bold')

            return redirect('salsa_auth:authenticate')

        else:
            messages.add_message(self.request,
                                 messages.ERROR,
                                 'Something went wrong',
                                 extra_tags='font-weight-bold')

            contact_message = (
                'You clicked an invalid activation link. Think you received this message in error? '
                'Contact our <a href="https://www.bettergov.org/team/jared-rutecki" target="_blank">Data Coordinator</a>.'
            )

            messages.add_message(self.request,
                                 messages.ERROR,
                                 contact_message)

            return redirect(settings.SALSA_AUTH_REDIRECT_LOCATION)


class Authenticate(RedirectView):
    url = settings.SALSA_AUTH_REDIRECT_LOCATION

    def get(self, *args, **kwargs):
        response = HttpResponseRedirect(self.url)

        response.set_cookie(
            settings.SALSA_AUTH_COOKIE_NAME,
            'true',
            expires=datetime.datetime.now() + datetime.timedelta(weeks=52),
            domain=settings.SALSA_AUTH_COOKIE_DOMAIN,
        )

        messages.add_message(self.request,
                             messages.INFO,
                             "We've logged you in so you can continue using the database.")

        return response
