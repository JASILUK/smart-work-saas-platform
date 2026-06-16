from apps.attendance.models.company_work_schedule import (
    CompanyWorkSchedule,
)


class CompanyWorkScheduleSelector:

    # =====================================================
    # BASE QUERYSET
    # =====================================================

    @staticmethod
    def get_queryset():

        return (

            CompanyWorkSchedule.objects

            .select_related(
                "company",
                "default_shift",
            )
        )

    # =====================================================
    # COMPANY SCHEDULE
    # =====================================================

    @staticmethod
    def get_company_schedule(
        *,
        company,
    ):

        return (

            CompanyWorkScheduleSelector

            .get_queryset()

            .filter(
                company=company,
                is_active=True,
            )

            .first()
        )

    # =====================================================
    # GET BY ID
    # =====================================================

    @staticmethod
    def get_by_id(
        *,
        schedule_id,
    ):

        return (

            CompanyWorkScheduleSelector

            .get_queryset()

            .filter(
                id=schedule_id,
            )

            .first()
        )

    # =====================================================
    # EXISTS FOR COMPANY
    # =====================================================

    @staticmethod
    def exists_for_company(
        *,
        company,
    ):

        return (

            CompanyWorkSchedule.objects

            .filter(
                company=company,
            )

            .exists()
        )
