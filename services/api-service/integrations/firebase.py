import firebase_admin

from django.conf import settings

from firebase_admin import credentials


firebase_app = None


def initialize_firebase():

    global firebase_app

    if firebase_app:
        return firebase_app

    credential_path = (
        settings.FIREBASE_CREDENTIALS
    )

    if not credential_path:

        raise Exception(
            "FIREBASE_CREDENTIALS is missing."
        )

    cred = credentials.Certificate(
        credential_path
    )

    firebase_app = (
        firebase_admin.initialize_app(
            cred
        )
    )

    return firebase_app