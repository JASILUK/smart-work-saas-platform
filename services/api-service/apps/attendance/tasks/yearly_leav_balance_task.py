import logging
from celery import shared_task
from django.utils import timezone
from apps.companies.models import Company
from apps.attendance.services.leave_provisioning_service import LeaveBalanceProvisioningService

logger = logging.getLogger(__name__)

@shared_task(name="apps.attendance.tasks.run_yearly_leave_allocation")
def run_yearly_leave_allocation_task(year_override=None):
    """
    Automated background task to pre-provision structural LeaveBalance rows 
    for the upcoming operational accounting calendar year cycle.
    """
    # Default execution footprint targets the upcoming year window (Current Year + 1)
    target_year = year_override or (timezone.now().year + 1)
    logger.info(f"[PROVISIONING_CRON] Initializing bulk leave allocation loop for year target: {target_year}")

    active_companies = Company.objects.filter(is_active=True)
    total_records_created = 0

    for company in active_companies:
        try:
            # Transaction boundaries are safely handled per company workspace within the service
            created_count = LeaveBalanceProvisioningService.provision_company_for_year(
                company=company,
                leave_year=target_year
            )
            total_records_created += created_count
            
            if created_count > 0:
                logger.info(f"  └─ Company Profile '{company.name}': Automatically provisioned {created_count} allocation rows.")
        
        except Exception as exc:
            # Isolates processing failures so a singular corrupt tenant profile cannot crash the pipeline
            logger.error(f"  └─ Critical error provisioning year {target_year} matrix for Company ID {company.id}: {str(exc)}", exc_info=True)

    logger.info(f"[PROVISIONING_CRON] System allocation completed. Net database rows initialized: {total_records_created}")
    return {"status": "SUCCESS", "records_created": total_records_created, "target_year": target_year}