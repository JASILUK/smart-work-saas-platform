from django.core.management.base import (
    BaseCommand,
)

from apps.companies.models import (
    Membership,
)

from apps.notifications.models import (
    NotificationPreference,
)


class Command(BaseCommand):

    help = (
        "Create missing notification "
        "preferences for memberships."
    )

    def handle(self, *args, **options):

        memberships = (
            Membership.objects.all()
        )

        created_count = 0

        for membership in memberships:

            _, created = (
                NotificationPreference.objects.get_or_create(
                    membership=membership
                )
            )

            if created:
                created_count += 1

        self.stdout.write(

            self.style.SUCCESS(

                f"Created "
                f"{created_count} "
                f"notification preferences."

            )
        )