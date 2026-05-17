from apps.notifications.models import (
    NotificationPreference,
)


class PreferenceService:

    # =====================================================
    # GET OR CREATE PREFERENCES
    # =====================================================

    @staticmethod
    def get_preferences(
        *,
        membership,
    ):

        preferences, _ = (
            NotificationPreference.objects
            .get_or_create(
                membership=membership,
            )
        )

        return preferences

    # =====================================================
    # UPDATE PREFERENCES
    # =====================================================

    @staticmethod
    def update_preferences(
        *,
        membership,
        data,
    ):

        preferences = (
            PreferenceService.get_preferences(
                membership=membership,
            )
        )

        allowed_fields = {
            "push_enabled",
            "sound_enabled",
            "chat_message_enabled",
            "mention_enabled",
            "meeting_enabled",
            "attendance_enabled",
            "system_enabled",
        }

        updated_fields = []

        for field, value in data.items():

            if field not in allowed_fields:
                continue

            setattr(
                preferences,
                field,
                value,
            )

            updated_fields.append(field)

        if updated_fields:

            preferences.save(
                update_fields=updated_fields,
            )

        return preferences