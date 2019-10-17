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

4. Use the sign up, log in, and log out views, as needed by your application.
