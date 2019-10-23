# 💃 django-salsa-auth

A reusable application to allow users of your Django application to
"authenticate" against your [Salsa](https://www.salsalabs.com/) user store.

## Quick start

1. Add `salsa_auth` to your `INSTALLED_APPS`:

    ```python
    INSTALLED_APPS = [
        ...
        'salsa_auth',
    ]
    ```

2. Include the `salsa_auth` URLs in your project URL conf:

    ```python
    path('salsa/', include('salsa_auth.urls')),
    ```

3. Run `python manage.py migrate` to create the `salsa_auth` models.

4. Add the following to your project settings, being sure to fill in real
values.


    ```python
    # Configure Django email backend: https://docs.djangoproject.com/en/2.2/topics/email/#smtp-backend
    EMAIL_USE_TLS = True
    EMAIL_HOST = ''  # e.g., smtp.gmail.com
    EMAIL_HOST_USER = ''  # e.g., youremail@email.com
    EMAIL_HOST_PASSWORD = ''
    EMAIL_PORT = 0  # e.g., 587

    # Configure salsa_auth
    SALSA_AUTH_API_KEY = ''  # https://help.salsalabs.com/hc/en-us/articles/224470007-Getting-Started#acquiring-a-token

    # Name and domain for cookie set for authorized users
    SALSA_AUTH_COOKIE_NAME = 'salsa-auth'
    SALSA_AUTH_COOKIE_DOMAIN = ''  # e.g., datamade.us

    # Location to which user will be redirected on authorization
    SALSA_AUTH_REDIRECT_LOCATION = '/'
    ```

5. Use the sign up, log in, and log out views, as needed by your application.
