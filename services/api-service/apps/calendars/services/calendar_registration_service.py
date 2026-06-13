from django.contrib.contenttypes.models import (
    ContentType,
)

from django.db import transaction

from apps.calendars.models.calendar_event_sync import (
    CalendarEventSync,
)

from apps.calendars.selectors.calendar_account_selector import (
    CalendarAccountSelector,
)

from apps.calendars.tasks.calendar_sync_tasks import (
    sync_calendar_event,
    delete_calendar_event,
)


class CalendarRegistrationService:

    # =====================================================
    # REGISTER OBJECT
    # =====================================================

    @classmethod
    def register(
        cls,
        *,
        membership,
        content_object,
    ):

        accounts = (
            CalendarAccountSelector
            .get_accounts(
                membership=membership,
            )
        )

        if not accounts.exists():

            return []

        content_type = (
            ContentType.objects
            .get_for_model(
                content_object
            )
        )

        sync_records = []

        for account in accounts:

            sync, created = (
                CalendarEventSync.objects
                .get_or_create(

                    calendar_account=
                        account,

                    content_type=
                        content_type,

                    object_id=
                        content_object.pk,

                    defaults={

                        "provider":
                            account.provider,

                        "sync_status":
                            CalendarEventSync
                            .SyncStatus
                            .PENDING,
                    },
                )
            )

            sync_records.append(
                sync
            )

            if created:

                transaction.on_commit(

                    lambda sync_id=sync.id:

                    sync_calendar_event.delay(
                        sync_id
                    )
                )

        return sync_records

    # =====================================================
    # RESYNC OBJECT
    # =====================================================

    @classmethod
    def resync(
        cls,
        *,
        content_object,
    ):

        content_type = (
            ContentType.objects
            .get_for_model(
                content_object
            )
        )

        syncs = (
            CalendarEventSync.objects
            .filter(
                content_type=content_type,
                object_id=content_object.pk,
            )
        )

        for sync in syncs:

            transaction.on_commit(

                lambda sync_id=sync.id:

                sync_calendar_event.delay(
                    sync_id
                )
            )

        return syncs

    # =====================================================
    # DELETE OBJECT
    # =====================================================

    @classmethod
    def mark_for_deletion(
        cls,
        *,
        content_object,
    ):

        content_type = (
            ContentType.objects
            .get_for_model(
                content_object
            )
        )

        syncs = (
            CalendarEventSync.objects
            .filter(
                content_type=content_type,
                object_id=content_object.pk,
            )
        )

        for sync in syncs:

            transaction.on_commit(

                lambda sync_id=sync.id:

                delete_calendar_event.delay(
                    sync_id
                )
            )

        return syncs