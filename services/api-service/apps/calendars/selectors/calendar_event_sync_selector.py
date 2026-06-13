# apps/calendars/selectors/calendar_event_sync_selector.py

from apps.calendars.models.calendar_event_sync import (
    CalendarEventSync,
)


class CalendarEventSyncSelector:

    # =====================================================
    # GET BY ID
    # =====================================================

    @staticmethod
    def get_by_id(
        *,
        sync_id,
    ):

        return (

            CalendarEventSync.objects
            .filter(
                id=sync_id,
            )
            .first()
        )

    # =====================================================
    # GET BY EXTERNAL EVENT ID
    # =====================================================

    @staticmethod
    def get_by_external_event_id(
        *,
        provider,
        external_event_id,
    ):

        return (

            CalendarEventSync.objects
            .filter(
                provider=provider,
                external_event_id=external_event_id,
            )
            .first()
        )

    # =====================================================
    # GET OBJECT SYNC
    # =====================================================

    @staticmethod
    def get_object_sync(
        *,
        content_type,
        object_id,
        calendar_account,
    ):

        return (

            CalendarEventSync.objects
            .filter(
                content_type=content_type,
                object_id=object_id,
                calendar_account=calendar_account,
            )
            .first()
        )

    # =====================================================
    # GET OBJECT SYNCS
    # =====================================================

    @staticmethod
    def get_object_syncs(
        *,
        content_type,
        object_id,
    ):

        return (

            CalendarEventSync.objects
            .filter(
                content_type=content_type,
                object_id=object_id,
            )
            .select_related(
                "calendar_account",
            )
        )

    # =====================================================
    # GET ACCOUNT SYNCS
    # =====================================================

    @staticmethod
    def get_account_syncs(
        *,
        calendar_account,
    ):

        return (

            CalendarEventSync.objects
            .filter(
                calendar_account=calendar_account,
            )
            .select_related(
                "content_type",
            )
        )

    # =====================================================
    # GET FAILED SYNCS
    # =====================================================

    @staticmethod
    def get_failed_syncs():

        return (

            CalendarEventSync.objects
            .filter(
                sync_status=
                CalendarEventSync.SyncStatus.FAILED,
            )
        )

    # =====================================================
    # GET PENDING SYNCS
    # =====================================================

    @staticmethod
    def get_pending_syncs():

        return (

            CalendarEventSync.objects
            .filter(
                sync_status=
                CalendarEventSync.SyncStatus.PENDING,
            )
        )

    # =====================================================
    # GET SYNCED SYNCS
    # =====================================================

    @staticmethod
    def get_synced_syncs():

        return (

            CalendarEventSync.objects
            .filter(
                sync_status=
                CalendarEventSync.SyncStatus.SYNCED,
            )
        )

    # =====================================================
    # HAS SYNC
    # =====================================================

    @staticmethod
    def has_sync(
        *,
        content_type,
        object_id,
        calendar_account,
    ):

        return (

            CalendarEventSync.objects
            .filter(
                content_type=content_type,
                object_id=object_id,
                calendar_account=calendar_account,
            )
            .exists()
        )