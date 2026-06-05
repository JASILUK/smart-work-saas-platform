
from asgiref.sync import sync_to_async

from django.conf import settings

from apps.meetings.services.attendance_service import (
    MeetingAttendanceService,
)

from apps.meetings.selectors.meeting_selectors import (
    MeetingSelector,
)

from apps.companies.selectors.Employee_selectors import (
    EmployeeSelector,
)

import redis


# =====================================================
# REDIS
# =====================================================

redis_client = redis.Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
)


# =====================================================
# REALTIME HANDLER
# =====================================================

class MeetingRealtimeHandler:

    # =================================================
    # INIT
    # =================================================

    def __init__(
        self,
        *,
        consumer,
    ):

        self.consumer = consumer

    # =================================================
    # MAIN ROUTER
    # =================================================

    async def handle(
        self,
        data,
    ):

        event_type = data.get(
            "type"
        )

        # =============================================
        # JOIN
        # =============================================

        if (
            event_type
            ==
            "join_meeting"
        ):

            await self.join_meeting(
                data=data,
            )

        # =============================================
        # LEAVE
        # =============================================

        elif (
            event_type
            ==
            "leave_meeting"
        ):

            await self.leave_meeting(
                data=data,
            )

    # =================================================
    # JOIN MEETING
    # =================================================

    async def join_meeting(
        self,
        *,
        data,
    ):

        meeting_id = data.get(
            "meeting_id"
        )

        if not meeting_id:
            return

        # =============================================
        # GET MEETING
        # =============================================

        meeting = await sync_to_async(
            MeetingSelector.get_by_public_id
        )(
            public_id=meeting_id,
            company=self.consumer.tenant_id,
        )

        if not meeting:
            return

        # =============================================
        # GET MEMBERSHIP
        # =============================================

        membership = await sync_to_async(
            EmployeeSelector.get_employee
        )(
            employee_id=self.consumer.membership_id,
            company=self.consumer.tenant_id
        )

        if not membership:
            return

        # =============================================
        # GROUP
        # =============================================

        meeting_group = (
            f"tenant_"
            f"{self.consumer.tenant_id}"
            f"_meeting_"
            f"{meeting_id}"
        )

        # =============================================
        # SUBSCRIBE SOCKET
        # =============================================

        await self.consumer.channel_layer.group_add(
            meeting_group,
            self.consumer.channel_name,
        )

        # =============================================
        # TRACK ACTIVE MEETING
        # =============================================

        self.consumer.active_meetings.add(
            str(meeting_id)
        )

        # =============================================
        # REDIS PRESENCE
        # =============================================

        presence_key = (
            self.get_meeting_presence_key(
                meeting_id=meeting_id,
            )
        )

        await sync_to_async(
            redis_client.sadd
        )(
            presence_key,
            str(
                self.consumer.membership_id
            ),
        )

        # =============================================
        # PERSIST ATTENDANCE
        # =============================================

        await MeetingAttendanceService.mark_joined(
            meeting=meeting,
            membership=membership,
        )

        # =============================================
        # BROADCAST SNAPSHOT
        # =============================================

        await self.broadcast_presence_snapshot(
            meeting_id=meeting_id,
        )

    # =================================================
    # LEAVE MEETING
    # =================================================

    async def leave_meeting(
        self,
        *,
        data,
    ):

        meeting_id = data.get(
            "meeting_id"
        )

        if not meeting_id:
            return

        # =============================================
        # GET MEETING
        # =============================================

        meeting = await sync_to_async(
            MeetingSelector.get_by_public_id
        )(
            public_id=meeting_id,
            company=self.consumer.tenant_id,
        )

        if not meeting:
            return

        # =============================================
        # GET MEMBERSHIP
        # =============================================

        membership = await sync_to_async(
            EmployeeSelector.get_employee
        )(
            employee_id=self.consumer.membership_id,
            company=self.consumer.tenant_id
        )

        if not membership:
            return

        # =============================================
        # GROUP
        # =============================================

        meeting_group = (
            f"tenant_"
            f"{self.consumer.tenant_id}"
            f"_meeting_"
            f"{meeting_id}"
        )

        # =============================================
        # REMOVE PRESENCE
        # =============================================

        presence_key = (
            self.get_meeting_presence_key(
                meeting_id=meeting_id,
            )
        )

        await sync_to_async(
            redis_client.srem
        )(
            presence_key,
            str(
                self.consumer.membership_id
            ),
        )

        # =============================================
        # UNSUBSCRIBE SOCKET
        # =============================================

        await self.consumer.channel_layer.group_discard(
            meeting_group,
            self.consumer.channel_name,
        )

        # =============================================
        # REMOVE ACTIVE MEETING
        # =============================================

        self.consumer.active_meetings.discard(
            str(meeting_id)
        )

        # =============================================
        # PERSIST ATTENDANCE
        # =============================================

        await MeetingAttendanceService.mark_left(
            meeting=meeting,
            membership=membership,
        )

        # =============================================
        # BROADCAST SNAPSHOT
        # =============================================

        await self.broadcast_presence_snapshot(
            meeting_id=meeting_id,
        )

    # =================================================
    # BROADCAST SNAPSHOT
    # =================================================

    async def broadcast_presence_snapshot(
        self,
        *,
        meeting_id,
    ):

        # =============================================
        # REDIS KEY
        # =============================================

        presence_key = (
            self.get_meeting_presence_key(
                meeting_id=meeting_id,
            )
        )

        # =============================================
        # ONLINE MEMBERS
        # =============================================

        online_members = (
            await sync_to_async(
                redis_client.smembers
            )(
                presence_key
            )
        )

        # =============================================
        # NORMALIZE IDS
        # =============================================

        online_members = [

            int(member_id)

            for member_id

            in online_members
        ]

        # =============================================
        # GROUP
        # =============================================

        meeting_group = (
            f"tenant_"
            f"{self.consumer.tenant_id}"
            f"_meeting_"
            f"{meeting_id}"
        )

        # =============================================
        # BROADCAST
        # =============================================

        await self.consumer.channel_layer.group_send(
            meeting_group,
            {
                "type": (
                    "meeting_presence_snapshot"
                ),

                "meeting_id": str(
                    meeting_id
                ),

                "online_members":
                    online_members,
            }
        )

    # =================================================
    # REDIS KEY
    # =================================================

    @staticmethod
    def get_meeting_presence_key(
        *,
        meeting_id,
    ):

        return (
            f"meeting_presence:"
            f"{meeting_id}"
        )

