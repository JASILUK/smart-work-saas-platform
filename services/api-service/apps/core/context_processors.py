from django.conf import settings


def global_branding(request):
    return {
        "APP_NAME": settings.APP_NAME,
        "SUPPORT_EMAIL": settings.SUPPORT_EMAIL,
        "LOGO_URL": settings.LOGO_URL,
    }
