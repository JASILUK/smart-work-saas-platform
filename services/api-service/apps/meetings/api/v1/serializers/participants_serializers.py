from rest_framework import serializers

from apps.meetings.models.participant import (
    MeetingParticipant,
)


# =========================================================
# OUTPUT
# =========================================================

class MeetingParticipantOutputSerializer(
    serializers.ModelSerializer
):

    membership_id = serializers.IntegerField(
        source="membership.id",
    )

    username = serializers.CharField(
        source="membership.user.username",
    )

    class Meta:

        model = MeetingParticipant

        fields = [
            "id",
            "membership_id",
            "username",
            "role",
            "status",
            "is_present",
            "can_invite",
            "can_moderate",
            "joined_at",
            "left_at",
            "created_at",
        ]


# =========================================================
# ADD PARTICIPANTS
# =========================================================

class MeetingParticipantAddSerializer(
    serializers.Serializer
):

    membership_ids = serializers.ListField(

        child=serializers.IntegerField(
            min_value=1,
        ),

        allow_empty=False,
    )


# =========================================================
# UPDATE ROLE
# =========================================================

class MeetingParticipantRoleUpdateSerializer(
    serializers.Serializer
):

    role = serializers.ChoiceField(
        choices=MeetingParticipant.Role.choices,
    )