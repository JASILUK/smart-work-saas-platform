# users/authentication.py
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken


class UniversalJWTAuthentication(JWTAuthentication):
    """
    Custom authentication that looks for the Access Token in the HttpOnly cookie first.
    If it is not there, it falls back to checking the standard Authorization header.
    """

    def authenticate(self, request):
        # 1. Look for the token in the secure cookie (Web Strategy)
        raw_token = request.COOKIES.get("access_token")

        # 2. If no cookie is found, let SimpleJWT check the headers! (Mobile Strategy)
        if not raw_token:
            return super().authenticate(request)

        # 3. If we DID find a cookie, validate it!
        try:
            # SimpleJWT decodes the token and checks the signature
            validated_token = self.get_validated_token(raw_token)

            # SimpleJWT finds the user in the database based on the token payload
            user = self.get_user(validated_token)

            # 4. THE MAGIC: We return a tuple of (user, token).
            # DRF takes this and automatically sets request.user = user!
            return (user, validated_token)

        except (InvalidToken, AuthenticationFailed):
            # If the token is expired or fake, return None.
            # DRF will automatically throw a 401 Unauthorized error.
            return None
