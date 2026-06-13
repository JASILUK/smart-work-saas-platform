# apps/calendars/services/calendar_sync_service.py

import json

from django.utils import timezone

from apps.calendars.models.calendar_event_sync import (
    CalendarEventSync,
)

from apps.calendars.integrations.factory import (
    CalendarProviderFactory,
)

from apps.calendars.builders.factory import (
    CalendarEventBuilderFactory,
)


class CalendarSyncService:

    # =====================================================
    # CREATE SYNC
    # =====================================================

    @staticmethod
    def create_sync(
        *,
        sync,
    ):

        provider = (
            CalendarProviderFactory
            .get_provider_for_account(
                account=sync.calendar_account,
            )
        )

        payload = (
            CalendarEventBuilderFactory
            .build_payload(
                content_object=sync.content_object,
            )
        )

        event = (
            provider.create_event(
                account=sync.calendar_account,
                event_data=payload,
            )
        )

        sync.external_event_id = (
            event["id"]
        )

        sync.sync_status = (
            CalendarEventSync
            .SyncStatus
            .SYNCED
        )

        sync.last_synced_at = (
            timezone.now()
        )

        sync.last_error = ""

        sync.save(
            update_fields=[
                "external_event_id",
                "sync_status",
                "last_synced_at",
                "last_error",
            ]
        )

        return sync

    # =====================================================
    # UPDATE SYNC
    # =====================================================

    @staticmethod
    def update_sync(
        *,
        sync,
    ):

        provider = (
            CalendarProviderFactory
            .get_provider_for_account(
                account=sync.calendar_account,
            )
        )

        payload = (
            CalendarEventBuilderFactory
            .build_payload(
                content_object=sync.content_object,
            )
        )

        provider.update_event(

            account=
                sync.calendar_account,

            external_event_id=
                sync.external_event_id,

            event_data=
                payload,
        )

        sync.sync_status = (
            CalendarEventSync
            .SyncStatus
            .SYNCED
        )

        sync.last_synced_at = (
            timezone.now()
        )

        sync.last_error = ""

        sync.save(
            update_fields=[
                "sync_status",
                "last_synced_at",
                "last_error",
            ]
        )

        return sync

    # =====================================================
    # DELETE SYNC
    # =====================================================

    @staticmethod
    def delete_sync(
        *,
        sync,
    ):

        if not sync.external_event_id:

            sync.sync_status = (
                CalendarEventSync
                .SyncStatus
                .DELETED
            )

            sync.last_synced_at = (
                timezone.now()
            )

            sync.save(
                update_fields=[
                    "sync_status",
                    "last_synced_at",
                ]
            )

            return sync

        provider = (
            CalendarProviderFactory
            .get_provider_for_account(
                account=sync.calendar_account,
            )
        )

        provider.delete_event(

            account=
                sync.calendar_account,

            external_event_id=
                sync.external_event_id,
        )

        sync.sync_status = (
            CalendarEventSync
            .SyncStatus
            .DELETED
        )

        sync.last_synced_at = (
            timezone.now()
        )

        sync.save(
            update_fields=[
                "sync_status",
                "last_synced_at",
            ]
        )

        return sync

    # =====================================================
    # MARK FAILED
    # =====================================================

    @staticmethod
    def mark_failed(
        *,
        sync,
        error,
    ):

        sync.sync_status = (
            CalendarEventSync
            .SyncStatus
            .FAILED
        )

        sync.last_error = str(error)

        sync.save(
            update_fields=[
                "sync_status",
                "last_error",
            ]
        )

        return sync