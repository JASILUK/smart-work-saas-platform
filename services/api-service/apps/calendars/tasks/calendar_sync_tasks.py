from celery import shared_task

from apps.calendars.selectors.calendar_event_sync_selector import (
    CalendarEventSyncSelector,
)

from apps.calendars.services.calendar_sync_service import (
    CalendarSyncService,
)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={
        "max_retries": 5,
    },
)
def sync_calendar_event(
    self,
    sync_id,
):

    sync = (
        CalendarEventSyncSelector
        .get_by_id(
            sync_id=sync_id,
        )
    )

    if not sync:

        return

    try:

        if sync.sync_status == (
            sync.SyncStatus.DELETED
        ):

            return

        if sync.external_event_id:

            CalendarSyncService.update_sync(
                sync=sync,
            )

        else:

            CalendarSyncService.create_sync(
                sync=sync,
            )

    except Exception as exc:

        CalendarSyncService.mark_failed(
            sync=sync,
            error=exc,
        )

        raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={
        "max_retries": 5,
    },
)
def delete_calendar_event(
    self,
    sync_id,
):

    sync = (
        CalendarEventSyncSelector
        .get_by_id(
            sync_id=sync_id,
        )
    )

    if not sync:

        return

    try:

        CalendarSyncService.delete_sync(
            sync=sync,
        )

    except Exception as exc:

        CalendarSyncService.mark_failed(
            sync=sync,
            error=exc,
        )

        raise