from django.urls import include, path, re_path

from salsa_auth import views as salsa_views


app_name = 'salsa_auth'
urlpatterns = [
    path('login/', salsa_views.LoginForm.as_view(), name='login'),
    path('signup/', salsa_views.SignUpForm.as_view(), name='signup'),
    path('verify/<uidb64>/<token>/', salsa_views.VerifyEmail.as_view(), name='verify'),
    path('authenticate', salsa_views.Authenticate.as_view(), name='authenticate'),
]
