# Automations

## Status: **Not Implemented**

No automation rules engine, triggers, actions, or APIs exist.

## What Exists Today (Plan Flag Only)

| Field | Location |
|-------|----------|
| `Plan.automation_enabled` | `apps/billing/models.py` |
| Exposed in plan serializer / seed | billing API |

No code checks `automation_enabled` before operations.

## Purpose (Intended)

Automation systems usually provide:

- Trigger definitions (event, schedule, webhook)
- Action chains (notify, assign, update record)
- Execution log per company
- Plan-gated feature via `automation_enabled`

## Architecture Recommendation

- Event bus or Celery-driven worker consuming domain signals
- Store rules as JSON schema or normalized tables
- Sandbox execution per tenant
- Idempotent action handlers

## Relationship to "Workflow" Comments

Comments like `# CREATE WORKFLOW` in `department_application_service.py` refer to **department creation steps**, not this automation product feature.

## Future Improvements

1. `apps.automations` with `Rule`, `Run` models
2. Check `request.subscription.plan.automation_enabled` in service layer
3. Integrate with notifications and chat system messages
4. Admin UI API for rule management
