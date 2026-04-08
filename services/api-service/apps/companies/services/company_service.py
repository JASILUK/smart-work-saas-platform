from apps.companies.models import Company


class CompanyService:

    def create_pending_company(self, *, owner, name):
        return Company.objects.create(
            name=name,
            slug=name.lower().replace(" ", "-"),
            owner=owner,
            status=Company.Status.PENDING,
        )

    def activate_company(self, *, company):
        company.status = Company.Status.ACTIVE
        company.save()
        return company
