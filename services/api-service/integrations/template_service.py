# integrations/template_service.py

from django.template.loader import render_to_string


class TemplateService:

    def render_email(self, template_name, context):
        return render_to_string(f"emails/{template_name}.html", context)

    def render_sms(self, template_name, context):
        return render_to_string(f"sms/{template_name}.txt", context)
