from apps.companies.models import Department
from apps.core.exceptions import ApplicationError
from apps.rbac.models import Role


class EmployeeService:

    def __init__(self, company, user):
        self.company = company
        self.user = user

    def update_employee(self, employee, data):

        role_id = data.get("role_id")
        department_id = data.get("department_id")

        if employee.user.id == self.user.id and employee.company.owner != self.user:
            raise ApplicationError(message="User Can't Change Yourself Himself!!")

        if role_id:
            role = Role.objects.filter(id=role_id, company=self.company).first()

            if not role:
                raise ApplicationError(message="Role not found in this company")
            if employee.role.name == "Owner" and self.user != employee.user:
                raise ApplicationError(message="You cant change Owner Data")

            if role.name == "Owner" and employee.role.name != "Owner":
                raise ApplicationError(message="Use ownership transfer API")

            employee.role = role

        if department_id:
            department = Department.objects.filter(
                id=department_id, company=self.company
            ).first()

            if not department:
                raise ApplicationError(message="Department not found in this company")

            employee.department = department
        else:
            employee.department = None

        if "name" in data:
            employee.user.name = data["name"]

        if "title" in data:
            employee.job_title = data["title"]

        employee.save()

        return employee

    def remove_employee(self, company, employee):

        if company.owner == employee:
            raise ApplicationError(message="You Can't Delete Owner")
        employee.delete()

    def block_employee(self, employee):

        if not employee.is_active:
            raise ApplicationError(message="Emplyee is already blocked ")
        if employee.user.id == self.user.id:
            raise ApplicationError(message="User Can't Block Himself!!")
        if employee.user == self.company.owner:
            raise ApplicationError(message="You Can't Block Owner")

        employee.is_active = False
        employee.save(update_fields=["is_active"])

        return employee

    def unblock_employee(self, employee):

        if employee.is_active:
            return employee
        if employee.user.id == self.user.id:
            raise ApplicationError(message="User Can't Unblock Himself!!")
        if employee.user == self.company.owner:
            raise ApplicationError(message="You Can't Unblock  Owner")

        employee.is_active = True
        employee.save(update_fields=["is_active"])

        return employee
