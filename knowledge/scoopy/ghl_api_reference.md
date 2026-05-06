# GHL API Reference (extracted from highlevel-api-docs)

Source: `C:/Users/Liam/Downloads/highlevel-api-docs/`. All citations are relative to that root.

## A. Inbound message webhook

**Schema doc:** `docs/webhook events/InboundMessage.md` (lines 22-76 message schema, 143-200 email schema).
There is **no** webhook payload schema inside `apps/marketplace.json` — webhook event shapes live only in `docs/webhook events/*.md`.

**Top-level payload fields (InboundMessage):**

```json
{
  "type": "InboundMessage",          // event type
  "locationId": "l1C08ntBrFjLS0elLIYU",
  "contactId": "cI08i1Bls3iTB9bKgFJh",
  "conversationId": "fcanlLgpbQgQhderivVs",
  "messageType": "SMS",              // SMS | Email | CALL | GMB | FB | IG | Live Chat
  "direction": "inbound",
  "body": "This is a test message",
  "contentType": "text/plain",
  "attachments": [],
  "dateAdded": "2021-04-21T11:31:45.750Z",
  "status": "delivered",
  "messageId": "...",                // present on call/email; sometimes absent on SMS example
  "userId": "...",                   // outbound only
  "conversationProviderId": "cI08i1Bls3iTB9bKgF01",
  "callDuration": 120,               // CALL only
  "callStatus": "completed"          // CALL only
}
```

Email variant adds: `emailMessageId`, `threadId`, `provider`, `to` (array), `cc`, `bcc`, `subject`, `from` (string).

**Possible event `type` values** (from `docs/webhook events/`):
`InboundMessage`, `OutboundMessage`, `ProviderOutboundMessage`, `ConversationUnreadWebhook`,
`AppointmentCreate`, `AppointmentUpdate`, `AppointmentDelete`,
`ContactCreate`, `ContactUpdate`, `ContactDelete`, `ContactDndUpdate`, `ContactTagUpdate`,
`TaskCreate`, `TaskComplete`, `TaskDelete`,
`NoteCreate`, `NoteUpdate`, `NoteDelete`,
`OpportunityCreate/Update/Delete/StageUpdate/StatusUpdate/AssignedToUpdate/MonetaryValueUpdate`,
`InvoiceCreate/Sent/Paid/PartiallyPaid/Void/Update/Delete`,
`OrderCreate`, `OrderStatusUpdate`,
`ProductCreate/Update/Delete`, `PriceCreate/Update/Delete`,
`LocationCreate`, `LocationUpdate`, `UserCreate`,
`AppInstall`, `AppUninstall`, `PlanChange`, `CampaignStatusUpdate`, `LCEmailStats`,
`AssociationCreate/Update/Delete`, `ObjectSchemaCreate/Update`, `RecordCreate/Update/Delete`, `RelationCreate/Delete`.

For the **Twilio messaging webhook** (used to land inbound SMS in GHL conversations): point Twilio's "A Message comes in" to `https://services.leadconnectorhq.com/conversations/providers/twilio/inbound_message` (cited: `InboundMessage.md` lines 223-235).

## B. Webhook signature verification

Source: `docs/oauth/WebhookAuthentication.md` (whole file).

- **Signed?** Yes.
- **Header:** `x-wh-signature`.
- **Algorithm:** **RSA-SHA256 with a public key (asymmetric)** — NOT HMAC. You verify with `crypto.createVerify('SHA256').verify(publicKey, signature, 'base64')` against the **raw request body**.
- **Secret:** A **global GHL public key** embedded in the doc (see lines 41-54). It is **not** the integration's private token, and **not** a per-subscription secret. Single public key, rotated occasionally (watch email/Slack channel — line 69).
- **Replay protection:** payload includes `timestamp` and `webhookId`. Reject if timestamp > ~5 min old, dedupe on `webhookId` (lines 59-66).

```js
// Node verification (from doc lines 78-100)
const verifier = crypto.createVerify('SHA256');
verifier.update(rawBody);                     // raw JSON body, not parsed
verifier.end();
verifier.verify(publicKey, signatureB64, 'base64');
```

Public key (PEM, copy verbatim from `WebhookAuthentication.md` lines 41-54):
```
-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAokvo/r9tVgcfZ5DysOSC
... (12 lines, see file)
-----END PUBLIC KEY-----
```

## C. Tasks API

Base: `apps/contacts.json`. API `Version` header: `2021-07-28`. Auth: bearer (private integration token works).

### GET `/contacts/{contactId}/tasks` — list tasks
- Cite: `apps/contacts.json` lines 146-217.
- Response: `{ "tasks": [TaskSchema] }` (line 2979).
- `TaskSchema` (line 2946): `id`, `title`, `body`, `assignedTo` (string user id), `dueDate` (ISO string), `completed` (bool), `contactId`.

### POST `/contacts/{contactId}/tasks` — create
- Cite: lines 218-308. Request body `CreateTaskParams` (line 2998).
- Required: **`title`, `dueDate`, `completed`** (line 3022-3026). Optional: `body`, `assignedTo`.
- Assignment field is **`assignedTo`** (string user id, e.g. `hxHGVRb1YJUscrCB8eXK`).
- Returns 201 with `{ "task": TaskSchema }`.

### PUT `/contacts/{contactId}/tasks/{taskId}` — update
- Cite: lines 392-492. Body `UpdateTaskBody` (line 3028) — same fields as create, **none required**.
- All fields updatable: `title`, `body`, `dueDate`, `completed`, `assignedTo`.

### PUT `/contacts/{contactId}/tasks/{taskId}/completed` — toggle complete only
- Cite: lines 575-…. Body `UpdateTaskStatusParams` = `{ "completed": bool }` (required).

### DELETE `/contacts/{contactId}/tasks/{taskId}` — delete
- Cite: lines 493-573.

**No `/tasks/{taskId}` top-level endpoint exists** — every task op is contact-scoped.

## D. Send conversation message

Source: `apps/conversations.json` lines 1348-1419. API `Version`: `2021-04-15`. Scope: `conversations/message.write`.

**POST `/conversations/messages`** — body `SendMessageBodyDto` (line 3746):

Required: **`type`, `subType`, `contactId`, `status`** (line 3930-3935).

`type` enum (line 3751-3761): `SMS`, `RCS`, `Email`, `WhatsApp`, `IG`, `FB`, `Custom`, `Live_Chat`, `TIKTOK`.

Other key fields:
- `message` (string, plain text) — used for SMS / generic text channels.
- `html` (string) — HTML body for email.
- `subject`, `emailFrom`, `emailTo`, `emailCc`, `emailBcc`, `replyMessageId`, `threadId`, `emailReplyMode` (`reply` | `reply_all`).
- `attachments` (array of URLs).
- `templateId` — optional. **Free-form `message` text is accepted; templates are NOT required.**
- `scheduledTimestamp` (UTC seconds), `fromNumber`, `toNumber`, `conversationProviderId`.
- `status` enum (line 3907-3912): `delivered`, `failed`, `pending`, `read`.

Minimal SMS example payload:
```json
{
  "type": "SMS",
  "subType": {},
  "contactId": "abc123",
  "message": "Hello from Scoopy",
  "status": "pending"
}
```

**Response `SendMessageResponseDto`** (line 3982):
```json
{
  "conversationId": "ABC12h2F6uBrIkfXYazb",
  "messageId": "t22c6DQcTDf3MjRhwf77",        // primary message id
  "emailMessageId": "rnGyqh2F6uBrIkfhFo9A",   // email only
  "messageIds": ["..."],                       // GMB only (multiple)
  "msg": "Message queued successfully."        // workflow messages
}
```

## E. Calendar events

Source: `apps/calendars.json`. API `Version`: `2021-04-15`. Scope: `calendars/events.readonly`.

### GET `/calendars/events` — list events for a window
- Cite: lines 703-825.
- **Required query:** `locationId`, `startTime` (millis epoch string), `endTime` (millis epoch string), AND one of `userId` / `calendarId` / `groupId`.
- Use `userId=<staff_user_id>` to get one user's upcoming events.
- Other endpoints: `/calendars/events/appointments` (POST create, line 458), `/calendars/events/appointments/{eventId}` (line 531), `/calendars/events/{eventId}` (line 1481, GET/DELETE), `/calendars/events/block-slots` (line 949).

### Calendar webhooks
- Yes — GHL emits `AppointmentCreate`, `AppointmentUpdate`, `AppointmentDelete` on calendar slot changes.
- Cite: `docs/webhook events/AppointmentCreate.md`, `AppointmentUpdate.md`, `AppointmentDelete.md`.
- Payload shape (AppointmentCreate.md lines 12-72): `{ type, locationId, appointment: { id, address, title, calendarId, contactId, groupId, appointmentStatus, assignedUserId, users[], notes, source, startTime, endTime, dateAdded, dateUpdated } }`.
- **No "calendar slot hit" / appointment-time-reached event** is documented. These events fire on CRUD only, not on the appointment's start time elapsing.

## Confirmed gaps / TODOs

1. **Webhook subscription model is undocumented in this repo.** `apps/marketplace.json` has zero matches for "webhook". How to subscribe a private integration / sub-account to specific event types (`InboundMessage`, `AppointmentCreate`, …) is not in the OpenAPI specs — this is configured in the GHL Marketplace UI per app, OR via the per-location "Webhook Trigger" workflow action. **Confirm with GHL: does a private integration token receive any webhooks, or do we need a Marketplace App?**
2. **No "appointment fires at start time" webhook.** If Scoopy needs to act when a calendar slot time arrives, we have to schedule it ourselves off `AppointmentCreate`/`Update` events.
3. **`subType` field on `SendMessageBodyDto` is documented as `type: object` with no enum or example structure** (line 3765-3768) but is `required`. We may need to send `{}` or omit — needs a live test.
4. **`SendMessageBodyDto.status` is required** in the schema but semantically odd for an outbound send call. Likely the API tolerates `"pending"`. Verify with test send.
5. **Public key rotation channel:** doc points to a Slack archive link for notifications. We need an alert mechanism (or just retry-with-fresh-key handling) — not in docs.
6. **Email Inbound payload example shows `from` and `subject` fields** (`InboundMessage.md` lines 215, 217) that are NOT in the declared email schema (lines 143-200). Schema is incomplete; treat fields as best-effort.
