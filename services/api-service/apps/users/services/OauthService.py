from apps.users.models import SocialAccount, User


class OAuthService:

    @staticmethod
    def get_or_create_user(provider, provider_id, email, extra_data):

        social = SocialAccount.objects.filter(
            provider=provider, provider_account_id=provider_id
        ).first()

        if social:
            return social.user

        user = User.objects.filter(email=email, is_verified=True).first()

        if not user:
            user = User.objects.create_user(email=email, is_verified=True)

        SocialAccount.objects.create(
            user=user,
            provider=provider,
            provider_account_id=provider_id,
            email=email,
            extra_data=extra_data,
        )

        return user
