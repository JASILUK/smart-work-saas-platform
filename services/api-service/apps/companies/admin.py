from django.contrib import admin

from apps.companies.models import Company, CompanyInvite, Membership

# Register your models here.

admin.site.register(Company)
admin.site.register(Membership)
admin.site.register(CompanyInvite)
