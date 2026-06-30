# apps/attendance/services/hr_record_detail_service.py
from apps.companies.models import Company
from apps.attendance.models.daily_attendance import DailyAttendance
from apps.attendance.selectors.hr_record_detail_selector import HRRecordDetailSelector

class HRRecordDetailService:
    """
    Assembles data modules and evaluates administrative workflow transitions 
    for the record detail panel view.
    """

    @classmethod
    def evaluate_allowed_actions(cls, record: DailyAttendance) -> dict:
        """
        Determines valid administrative actions based on the payroll locking status 
        and compliance state flags of the record.
        """
        is_locked = record.finalized_at is not None
        has_review_flags = record.needs_review

        return {
            "can_finalize": not is_locked and not has_review_flags,
            "can_unlock": is_locked,
            "can_reprocess": not is_locked,
            "can_manual_correction": not is_locked,
            "can_checkin_override": not is_locked,
            "can_checkout_override": not is_locked
        }

    @classmethod
    def compile_detailed_record_packet(cls, *, company: Company, record_id: int) -> Optional[dict]:
        """
        Queries and maps selectors and permission schemas into a structured dictionary.
        """
        data_graph = HRRecordDetailSelector.get_comprehensive_record_graph(
            company=company, 
            record_id=record_id
        )
        
        if not data_graph:
            return None
            
        record, events, audit_history = data_graph
        allowed_actions = cls.evaluate_allowed_actions(record)

        return {
            "record": record,
            "timeline": events,
            "audit_history": audit_history,
            "allowed_actions": allowed_actions
        }