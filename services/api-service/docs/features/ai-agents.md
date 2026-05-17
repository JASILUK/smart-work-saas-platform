# AI Agents

## Status: **Not Implemented**

No AI agent models, orchestration services, LLM integration layer, or APIs exist in this API service.

## What Exists Today (Billing Stub Only)

| Field | Model |
|-------|-------|
| `Plan.ai_credits_per_month` | `apps/billing/models.py` |
| Seeded in | `management/commands/seed_plans.py` |

This reserves **commercial metering** for a future AI feature but provides no runtime enforcement or credit consumption tracking.

## Purpose (Intended)

A future AI agents module would typically include:

- Agent definitions per company
- Prompt/tool configuration
- Credit usage ledger tied to `ai_credits_per_month`
- Async job execution (Celery) for long-running inference
- Audit logging for compliance

## Architecture Recommendation

- Separate app or external AI microservice with API key auth
- Do not embed API keys in Django settings without vault
- Rate limit and tenant-isolate all prompts/context
- If using chat: optional `Message` type or separate `AIConversation` to avoid polluting user chat

## Security Considerations

- Prompt injection via user content
- PII leakage to third-party LLM providers
- Per-tenant API key rotation

## Future Improvements

1. Credit ledger table + decrement on usage
2. Enforce plan limit in middleware or service decorator
3. Agent CRUD API and webhook callbacks
4. Document integration contract for frontend
