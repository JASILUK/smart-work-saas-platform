from apps.companies.models import Department
from apps.core.exceptions import ApplicationError
from apps.rbac.models import Role


class EmployeeService:

    def __init__(self, company, user):

        self.company = company
        self.user = user

    def update_employee(
        self,
        employee,
        data,
    ):

        role_id = data.get("role_id")

        # distinguish omitted vs explicit null
        department_provided = (
            "department_id" in data
        )

        department_id = data.get(
            "department_id"
        )

        # =================================================
        # SELF UPDATE PROTECTION
        # =================================================

        if (
            employee.user.id == self.user.id
            and employee.company.owner != self.user
        ):

            raise ApplicationError(
                message=(
                    "User can't modify "
                    "their own employee record."
                )
            )

        # =================================================
        # ROLE
        # =================================================

        if role_id:

            role = Role.objects.filter(
                id=role_id,
                company=self.company,
            ).first()

            if not role:

                raise ApplicationError(
                    message=(
                        "Role not found "
                        "in this company."
                    )
                )

            if (
                employee.role.name == "Owner"
                and self.user != employee.user
            ):

                raise ApplicationError(
                    message=(
                        "You can't modify "
                        "the owner role."
                    )
                )

            if (
                role.name == "Owner"
                and employee.role.name != "Owner"
            ):

                raise ApplicationError(
                    message=(
                        "Use the ownership "
                        "transfer API."
                    )
                )

            employee.role = role

        # =================================================
        # DEPARTMENT
        # =================================================

        if department_provided:

            if department_id:

                department = (
                    Department.objects.filter(
                        id=department_id,
                        company=self.company,
                    ).first()
                )

                if not department:

                    raise ApplicationError(
                        message=(
                            "Department not found "
                            "in this company."
                        )
                    )

                employee.department = (
                    department
                )

            else:

                # explicit removal
                employee.department = None

        # =================================================
        # USER NAME
        # =================================================

        if "name" in data:

            employee.user.name = (
                data["name"]
            )

            employee.user.save(
                update_fields=["name"]
            )

        # =================================================
        # JOB TITLE
        # =================================================

        if "title" in data:

            employee.job_title = (
                data["title"]
            )

        # =================================================
        # WORK MODE
        # =================================================

        if "work_mode" in data:

            employee.work_mode = (
                data["work_mode"]
            )

        # =================================================
        # SAVE MEMBERSHIP
        # =================================================

        employee.save()

        return employee

    def remove_employee(
        self,
        company,
        employee,
    ):

        if company.owner == employee:

            raise ApplicationError(
                message="You can't delete Owner."
            )

        employee.delete()

    def block_employee(
        self,
        employee,
    ):

        if not employee.is_active:

            raise ApplicationError(
                message=(
                    "Employee is already blocked."
                )
            )

        if employee.user.id == self.user.id:

            raise ApplicationError(
                message=(
                    "User can't block himself."
                )
            )

        if employee.user == self.company.owner:

            raise ApplicationError(
                message=(
                    "You can't block Owner."
                )
            )

        employee.is_active = False

        employee.save(
            update_fields=[
                "is_active",
            ]
        )

        return employee

    def unblock_employee(
        self,
        employee,
    ):

        if employee.is_active:

            return employee

        if employee.user.id == self.user.id:

            raise ApplicationError(
                message=(
                    "User can't unblock himself."
                )
            )

        if employee.user == self.company.owner:

            raise ApplicationError(
                message=(
                    "You can't unblock Owner."
                )
            )

        employee.is_active = True

        employee.save(
            update_fields=[
                "is_active",
            ]
        )

        return employee