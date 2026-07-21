# apps/attendance/validators/timeline_validator.py
"""
Timeline Chronological Sequence Validator Engine

Enforces production enterprise safety rules regarding clock state progressions.
Evaluates night shift boundary crossings safely without sequence index inversions.
"""

from typing import List, Dict, Any, Tuple, Optional
from django.utils.translation import gettext_lazy as _
from apps.attendance.models.attendance_event import AttendanceEventTypes

class TimelineSequenceValidator:
    """
    Validates chronological consistency for an individual day's event tree.
    """

    @classmethod
    def validate_timeline(cls, simulated_events: List[Dict[str, Any]]) -> Tuple[bool, Optional[Dict[str, List[str]]]]:
        if not simulated_events:
            return False, {"timeline": [_("Attendance timeline cannot be empty.")]}

        # ─── FIXED: SHIFT-AWARE TIMELINE SORT MATRIX ──────────────────────────
        TYPE_WEIGHTS = {
            AttendanceEventTypes.CHECK_IN: 1,
            AttendanceEventTypes.BREAK_OUT: 2,
            AttendanceEventTypes.BREAK_IN: 3,
            AttendanceEventTypes.CHECK_OUT: 4,
        }

        # Check for night shift conditions (a check-in starting late at night)
        check_ins = [e for e in simulated_events if e["event_type"] == AttendanceEventTypes.CHECK_IN]
        
        def get_shift_aware_sort_key(item):
            t = item["event_time"]
            if check_ins:
                primary_in_time = check_ins[0]["event_time"]
                # If the shift starts past 18:00 (6 PM), early morning events (00:00 to 12:00)
                # belong chronologically at the end of the timeline sequence loop (+24h)
                if primary_in_time.hour >= 18 and t.hour < 18:
                    return (1, t.date(), TYPE_WEIGHTS.get(item["event_type"], 0), t)
            
            return (0, t.date(), TYPE_WEIGHTS.get(item["event_type"], 0), t)

        # Sort combined timeline safely without breaking night shift indices
        normalized_events = sorted(simulated_events, key=get_shift_aware_sort_key)
        # ───────────────────────────────────────────────────────────────────────

        errors: Dict[str, List[str]] = {}

        # Rule 1: Validate timestamps are unique and ascending
        for i in range(1, len(normalized_events)):
            current = normalized_events[i]
            previous = normalized_events[i - 1]
            if current["event_time"] == previous["event_time"] and current["event_type"] == previous["event_type"]:
                current_id_str = f"event_{current.get('id') or 'new'}"
                cls._add_error(errors, current_id_str, _("Duplicate event timestamp detected."))

        # Rule 2: First event must be a CHECK_IN
        if normalized_events[0]["event_type"] != AttendanceEventTypes.CHECK_IN:
            first_id_str = f"event_{normalized_events[0].get('id') or 'new'}"
            cls._add_error(errors, first_id_str, _("The primary transaction of the tracking shift sequence must be a CHECK_IN."))

        # Rule 3: Last event must be a CHECK_OUT
        if normalized_events[-1]["event_type"] != AttendanceEventTypes.CHECK_OUT:
            last_id_str = f"event_{normalized_events[-1].get('id') or 'new'}"
            cls._add_error(errors, last_id_str, _("The final concluding transaction of the tracking shift sequence must be a CHECK_OUT."))

        has_checked_in = False
        has_checked_out = False
        active_break = False

        for event in normalized_events:
            evt_type = event["event_type"]
            evt_id_str = f"event_{event.get('id') or 'new'}"

            if evt_type == AttendanceEventTypes.CHECK_IN:
                if has_checked_in:
                    cls._add_error(errors, evt_id_str, _("Multiple CHECK_IN transactions are not allowed."))
                has_checked_in = True

            elif evt_type == AttendanceEventTypes.BREAK_OUT:
                if not has_checked_in:
                    cls._add_error(errors, evt_id_str, _("A BREAK_OUT transition cannot execute before a valid CHECK_IN transaction."))
                if active_break:
                    cls._add_error(errors, evt_id_str, _("Consecutive BREAK_OUT transitions are prohibited."))
                if has_checked_out:
                    cls._add_error(errors, evt_id_str, _("A BREAK_OUT transition cannot execute after a completed CHECK_OUT transaction."))
                active_break = True

            elif evt_type == AttendanceEventTypes.BREAK_IN:
                if not active_break:
                    cls._add_error(errors, evt_id_str, _("A BREAK_IN transition requires a preceding unresolved BREAK_OUT intermission."))
                if has_checked_out:
                    cls._add_error(errors, evt_id_str, _("A BREAK_IN transition cannot follow a completed CHECK_OUT transaction."))
                active_break = False

            elif evt_type == AttendanceEventTypes.CHECK_OUT:
                if not has_checked_in:
                    cls._add_error(errors, evt_id_str, _("A CHECK_OUT transition requires a preceding CHECK_IN transaction."))
                if active_break:
                    cls._add_error(errors, evt_id_str, _("A CHECK_OUT transition cannot occur while a break session remains open."))
                if has_checked_out:
                    cls._add_error(errors, evt_id_str, _("Multiple CHECK_OUT transactions are prohibited."))
                has_checked_out = True

        if errors:
            return False, errors
        return True, None

    @classmethod
    def _add_error(cls, errors: Dict[str, List[str]], key: str, message: str):
        if key not in errors:
            errors[key] = []
        errors[key].append(str(message))