import datetime
from celery import shared_task
from apps.companies.models import Company
from apps.attendance.services.daily_attendance_engine import DailyAttendanceEngine


@shared_task(name="attendance.tasks.finalize_yesterday_attendance")
def finalize_yesterday_attendance() -> str:
    """ Runs Nightly at 01:00 AM UTC. Compiles delta timelines blocks. """
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    companies = Company.objects.all()
    compiled_count = 0
    
    for comp in companies:
        active_staff = comp.memberships.filter(is_active=True)
        for staff in active_staff:
            try:
                DailyAttendanceEngine.build_daily_attendance(company=comp, membership=staff, target_date=yesterday)
                compiled_count += 1
            except Exception:
                continue
                
    return f"Successfully generated summaries ledgers for {compiled_count} workspace profiles segments."


@shared_task(name="attendance.tasks.auto_close_missing_checkouts")
def auto_close_missing_checkouts() -> str:
    """ Runs Hourly. Targets unclosed boundary timeouts parameters switches. """
    today = datetime.date.today()
    companies = Company.objects.all()
    total_closed = 0
    
    for comp in companies:
        total_closed += DailyAttendanceEngine.auto_finalize_missing_checkout(company=comp, target_date=today)
        
    return f"Enforced auto-checkout corrections parameters parameters switches across {total_closed} incomplete records."