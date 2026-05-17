# Chat

## Purpose

Tenant-scoped messaging: direct messages, groups, department channels, message delivery/read receipts, media attachments, and realtime sync over WebSockets.

## Business Requirements

- All conversations belong to a `Company`
- Chat actors are `Membership` records, not `User`
- Support text and media messages with replies
- System messages for group lifecycle events
- Unread counts and sidebar previews
- Offline push via notifications app

## Models

| Model | Responsibility |
|-------|----------------|
| `Conversation` | UUID PK; types: direct, group, department, project (project not implemented) |
| `ConversationParticipant` | Per-membership settings: unread, mute, pin, chat_role |
| `Message` | Content/media; soft delete; system events |
| `MessageStatus` | Per-recipient sent/delivered/read |

## Architecture

| Module | Role |
|--------|------|
| `chat_service.py` | Conversation creation (direct) |
| `message_service.py` | Send, edit, delete, broadcast, notifications |
| `group_service.py` | Group CRUD, members, roles |
| `group_realtime_service.py` | WS events for groups |
| `department_chat_service.py` | Department channel sync |
| `system_message_service.py` | System event messages |
| `MessageService.py` | Cursor pagination helper |
| `TenantConsumer` | WS client protocol |

## Services

### `MessageService.send_message`

Transactional pipeline:

1. Participant authorization
2. File upload → Cloudinary if present
3. Create `Message`
4. `_handle_delivery` — unread increment (skip if viewer in Redis room set), bulk `MessageStatus`, update `last_message`
5. `_broadcast_message` — channel layer to room + user groups
6. `_send_notifications` — FCM for offline recipients

### Group operations (`group_service`)

Create group, add/remove members, role updates, leave — each emits system messages and realtime events.

## Selectors

- `get_direct_conversation`
- `get_user_conversations`
- `get_conversation_messages`

## Serializers

`apps/chat/api/v1/serializers.py` — conversation list, message payloads, group forms.

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `conversations/` | GET | List user conversations |
| `conversations/<uuid>/messages/` | GET | Message history (cursor) |
| `conversations/<uuid>/read/` | POST | Mark read (HTTP) |
| `direct/` | POST | Open/create DM |
| `messages/send/` | POST | Send message |
| `messages/<uuid>/` | PATCH/DELETE | Edit/delete |
| `messages/<uuid>/info/` | GET | Delivery/read info |
| `groups/` | POST | Create group |
| `groups/<uuid>/` | GET | Group details |
| `groups/<uuid>/members/` | POST | Add members |
| `groups/<uuid>/members/remove/` | POST | Remove |
| `groups/<uuid>/leave/` | POST | Leave |
| `groups/<uuid>/roles/` | PATCH | Update participant role |
| `groups/<uuid>/settings/` | PATCH | Group metadata |
| `ws-ticket/` | POST | WebSocket auth ticket |

Uses `BaseCompanyAPIView` (or equivalent) — requires `X-Company-ID`.

## Permissions & Roles

- Tenant RBAC on HTTP views where configured
- **Message send:** participant check in service, not permission code
- **WebSocket room join:** no participant validation (known gap)

## Realtime/WebSocket Flows

See [../websocket/realtime-message-flow.md](../websocket/realtime-message-flow.md).

Connect: `ws/app/?ticket=...`

Events: `chat_message`, `sidebar_update`, `status_update`, typing, presence.

## Validation Rules

- Text messages require non-empty content
- Media requires uploaded file
- Reply target must be same conversation
- Non-participants cannot send
- Deleted messages show placeholder in previews

## Security Considerations

- Fix room join authorization
- Validate company_id on conversation matches membership company
- File upload size/type limits for production
- Rate limit message send per membership

## Scalability Concerns

- `MessageStatus` row explosion
- Connect-time bulk delivery update
- Group broadcast fan-out
- Redis room set per conversation — memory at scale

## Future Improvements

- Implement or remove `PROJECT` conversation type
- Message search (PostgreSQL full-text or external index)
- E2E encryption (not present)
- Consolidate duplicate service modules
- Remove dead consumer files or wire them
