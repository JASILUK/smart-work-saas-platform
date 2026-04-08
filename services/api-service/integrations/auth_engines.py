# users/services/auth_engines.py
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import User


class JWTAuthEngine:
    def issue(self, user: User) -> dict:
        """Generates standard JWT tokens and returns them as a simple dictionary."""
        refresh = RefreshToken.for_user(user)
        return {"access": str(refresh.access_token), "refresh": str(refresh)}
