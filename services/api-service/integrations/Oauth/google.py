import requests
from django.conf import settings


class GoogleOAuthService:

    VERIFY_URL = "https://oauth2.googleapis.com/tokeninfo"

    @staticmethod
    def verify_token(id_token):

        response = requests.get(
            GoogleOAuthService.VERIFY_URL, params={"id_token": id_token}, timeout=5
        )

        if response.status_code != 200:
            raise Exception("Invalid Google token")

        data = response.json()

        if data["aud"] != settings.GOOGLE_CLIENT_ID:
            raise Exception("Token was not issued for this app")

        return {
            "provider_id": data["sub"],
            "email": data["email"],
            "name": data.get("name"),
            "avatar": data.get("picture"),
        }
