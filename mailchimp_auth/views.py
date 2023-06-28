import datetime
import logging
from uuid import uuid4

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.views.generic import FormView, RedirectView
import requests

from mailchimp_auth.constants import TEST_PRIVATE_KEY
from mailchimp_auth.forms import SignUpForm, LoginForm
from mailchimp_auth.models import UserZipCode
from mailchimp_auth.mailchimp import client as mailchimp_client
from mailchimp_auth.tokens import account_activation_token


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
        email = form.cleaned_data['email']

        token = form.data['g-recaptcha-response']

        try:
            score = self._get_captcha_score(token)
        except ValidationError:
            raise
        except requests.exceptions.ContentDecodingError:
            raise ValidationError('Could not get reCAPTCHA score')
        else:
            user_is_a_bot = score < getattr(settings, 'GOOGLE_CAPTCHA_BOT_THRESHOLD', 0.1)

            user_might_be_a_bot = (
                score > getattr(settings, 'GOOGLE_CAPTCHA_BOT_THRESHOLD', 0.1) and
                score < getattr(settings, 'GOOGLE_CAPTCHA_UNCERTAIN_THRESHOLD', 0.5)
            )

            if user_is_a_bot:
                return super().form_invalid(form)

            elif user_might_be_a_bot:
                logging.warning(
                    'CAPTCHA validation failed for signup: {}'.format(email)
                )

                message_title = 'Validation Error'
                message_body = (
                    'We could not validate your email address. Please contact our '
                    '<a href="mailto:help@illinoisanswers.org" target="_blank">Data Coordinator</a>.'
                )

                messages.add_message(self.request, messages.INFO, message_title, extra_tags='font-weight-bold')
                messages.add_message(self.request, messages.INFO, message_body)

                return super().form_invalid(form)

        # If the email already exists in Mailchimp, re-verification is not required.
        # Authenticate the user.
        mailchimp_user = mailchimp_client.get_supporter(email)

        if mailchimp_user == 'error':
            message_title = 'Something went wrong, please try again.'
            message_body = (
                '<p>If you continue encountering problems accessing the database, '
                'please contact our <a href="mailto:help@illinoisanswers.org" target="_blank">Data Coordinator</a>.'
            )

            messages.add_message(self.request, messages.INFO, message_title, extra_tags='font-weight-bold')
            messages.add_message(self.request, messages.INFO, message_body)
        elif mailchimp_user:
            # Sometimes the user's first name is not in Mailchimp.
            welcome_message = 'Welcome back, {}!'.format(mailchimp_user['merge_fields'].get('FNAME', email))  

            messages.add_message(self.request,
                                 messages.INFO,
                                 welcome_message,
                                 extra_tags='font-weight-bold')

            self.redirect_url = reverse('mailchimp_auth:authenticate')

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
                'please contact our <a href="mailto:help@illinoisanswers.org" target="_blank">Data Coordinator</a>.'
            )

            messages.add_message(self.request, messages.INFO, message_title, extra_tags='font-weight-bold')
            messages.add_message(self.request, messages.INFO, message_body)

        return super().form_valid(form)

    def _get_captcha_score(self, token):
        captcha_response_token = token

        if captcha_response_token is None:
            raise ValidationError('Submitted form is missing g-recaptcha-response field')

        siteverify_url = 'https://www.google.com/recaptcha/api/siteverify'

        captcha_response = requests.post(siteverify_url, data={
            'secret': getattr(settings, 'RECAPTCHA_PRIVATE_KEY', TEST_PRIVATE_KEY),
            'response': captcha_response_token,
            'remoteip': self.request.META.get('HTTP_X_FORWARDED_FOR', '') or self.request.META.get('REMOTE_ADDR', ''),
        })

        captcha_response.raise_for_status()

        captcha_response_data = captcha_response.json()

        response_failed = (captcha_response_data.get('success') is None or
                           captcha_response_data.get('score') is None)

        if response_failed:
            msg = 'Malformed reCAPTCHA response: {}'.format(captcha_response_data)
            raise requests.exceptions.ContentDecodingError(msg)

        return captcha_response_data['score']

    def _make_user(self, form_data):
        form_data.pop('address')

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
    redirect_url = '/mailchimp/authenticate'

    def post(self, *args, **kwargs):
        form = self.get_form()

        if form.is_valid():
            user = mailchimp_client.get_supporter(form.cleaned_data['email'])

            if not user:
                error_message = (
                    '<strong>{email}</strong> is not subscribed to the BGA mailing list. Please '
                    '<a href="javascript://" class="toggle-login-signup" data-parent_modal="loginModal">sign up</a> '
                    'to access this tool.'
                )
                form.errors['email'] = [error_message.format(email=form.cleaned_data['email'])]
                return self.form_invalid(form)
            elif user == 'error':
                error_message = (
                    '<p>Something went wrong, please try again. If you continue encountering problems accessing the database, '
                    'please contact our <a href="mailto:help@illinoisanswers.org" target="_blank">Data Coordinator</a>.'
                )
                form.errors['email'] = [error_message.format(email=form.cleaned_data['email'])]
                return self.form_invalid(form)

            try:
                greeting_name = user['merge_fields']['FNAME']
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
            mailchimp_user = mailchimp_client.put_supporter(user)

            if mailchimp_user == 'error':
                messages.add_message(self.request,
                    messages.ERROR,
                    'Something went wrong',
                    extra_tags='font-weight-bold')

                error_message = (
                    'Please try to use the activation link again. If you continue encountering problems accessing the database, '
                    'please contact our <a href="mailto:help@illinoisanswers.org" target="_blank">Data Coordinator</a>.'
                )

                messages.add_message(self.request,
                                    messages.ERROR,
                                    error_message)
                return redirect(settings.MAILCHIMP_AUTH_REDIRECT_LOCATION)
            else:
                email = mailchimp_user['email_address']
                messages.add_message(self.request,
                                    messages.INFO,
                                    'Welcome back, {}!'.format(mailchimp_user['merge_fields'].get('FNAME', email)),
                                    extra_tags='font-weight-bold')

                return redirect('mailchimp_auth:authenticate')

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

            return redirect(settings.MAILCHIMP_AUTH_REDIRECT_LOCATION)


class Authenticate(RedirectView):
    url = settings.MAILCHIMP_AUTH_REDIRECT_LOCATION

    def get(self, *args, **kwargs):
        response = HttpResponseRedirect(self.url)

        response.set_cookie(
            settings.MAILCHIMP_AUTH_COOKIE_NAME,
            'true',
            expires=datetime.datetime.now() + datetime.timedelta(weeks=52),
            domain=settings.MAILCHIMP_AUTH_COOKIE_DOMAIN,
        )

        messages.add_message(self.request,
                             messages.INFO,
                             "We've logged you in so you can continue using the database.")

        return response
