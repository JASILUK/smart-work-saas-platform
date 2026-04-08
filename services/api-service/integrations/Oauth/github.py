import requests
from django.conf import settings


class GithubOAuthService:

    USER_URL = "https://api.github.com/user"

    @staticmethod
    def get_user(access_token):

        headers = {"Authorization": f"Bearer {access_token}"}

        response = requests.get(GithubOAuthService.USER_URL, headers=headers)

        data = response.json()

        return {
            "provider_id": data["id"],
            "email": data["email"],
            "name": data["login"],
        }
