from django.urls import include, path, re_path

from mailchimp_auth import views as mailchimp_views


app_name = 'mailchimp_auth'
urlpatterns = [
    path('login/', mailchimp_views.LoginForm.as_view(), name='login'),
    path('signup/', mailchimp_views.SignUpForm.as_view(), name='signup'),
    path('verify/<uidb64>/<token>/', mailchimp_views.VerifyEmail.as_view(), name='verify'),
    path('authenticate', mailchimp_views.Authenticate.as_view(), name='authenticate'),
]
