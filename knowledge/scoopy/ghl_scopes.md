# Scoopy's GHL API Scopes

The private integration token Scoopy uses (env var `GHL_API_KEY`) has the following scopes on the Scoop Patrol GHL location. **If you find yourself wanting to use a scope not listed here, STOP and ask Liam to add it — don't pretend a tool will work.**

## Contacts
- `contacts.readonly` — read contact data
- `contacts.write` — update contact custom fields, basic info

## Conversations & messaging
- `conversations.readonly` / `conversations.write`
- `conversations/message.readonly` — read message history
- `conversations/message.write` — **send SMS / email / WhatsApp** to customers
- `conversations/reports.readonly`

## Tasks
- `locations/tasks.readonly` — fetch a contact's tasks (used to find `[REPLY]` and `[ACTION]` tasks)
- `locations/tasks.write` — **create, update, complete tasks** (Scoopy's queue)
- `recurring-tasks.readonly` / `recurring-tasks.write`

## Tags
- `locations/tags.readonly` — read tags
- `locations/tags.write` — add/remove tags (used for "disappearing tag" trigger pattern)

## Calendars (for the agent-as-user calendar trigger pattern)
- `calendars.readonly` / `calendars.write`
- `calendars/events.readonly` / `calendars/events.write`
- `calendars/groups.readonly` / `calendars/groups.write`
- `calendars/resources.readonly` / `calendars/resources.write`

## Custom fields & values
- `locations/customFields.readonly` / `locations/customFields.write` — read/update field schemas
- `locations/customValues.readonly` / `locations/customValues.write` — location-level values

## Invoices & billing
- `invoices.readonly` / `invoices.write`
- `invoices/schedule.readonly` / `invoices/schedule.write` — recurring schedules
- `invoices/template.readonly` / `invoices/template.write`
- `payments/coupons.readonly` / `payments/coupons.write`
- `payments/transactions.readonly`
- `payments/subscriptions.readonly` (note: scope is named "Edit Payment Transactions" in UI but maps to subscriptions read)
- `payments/orders.readonly` / `payments/orders.write`
- `saas/location.read` / `saas/location.write`

## Products
- `products.readonly` / `products.write`
- `products/prices.readonly` / `products/prices.write`
- `products/collection.readonly` / `products/collection.write`

## Forms, opportunities, etc.
- `forms.readonly` / `forms.write`
- `opportunities.readonly` / `opportunities.write`
- `campaigns.readonly`
- `phonenumbers.read`

## Read-only on users
- `users.readonly` — Scoopy can read user info but **cannot modify users**

## What Scoopy CANNOT do
- **No deletes anywhere** — no contact deletion, no task deletion, no message deletion
- **No user management writes**
- **No SaaS subscription edits** beyond reads
- **No bulk-destructive operations** in general

If the right course of action requires anything not on this list, escalate to Liam — don't try to work around it.
