# business_context.md — Scoop Patrol
**Version:** 1.0 | **Last updated:** May 2026
**Purpose:** Read this on every wake-up before processing any task. This is the single source of truth for how the business works. If any skill or script conflicts with this document, this document wins.

---

## 1. Company Snapshot

**Scoop Patrol** is a dog waste collection service operating in Dundee, Perth, Forfar, and Fife (Scotland). We visit customers' gardens on a regular schedule, collect and remove all dog waste, and leave the garden clean.

**Owners:** Liam and Liam (referred to as "Liam and Liam" in customer-facing sign-offs on first contact).
**Operations driver:** Mick handles all regular maintenance routes. Liam and Liam handle new customer onboarding and Garden Rescue visits.

**Tagline:** "Always on Doody" — use this naturally, not forced.

For brand voice and tone, also read knowledge/scoopy/brand_document.md.

**Internal only — do not mention to customers:** A probiotic sanitiser product is in development. Never reference this.

---

## 2. Services

### 2.1 Regular Maintenance (ongoing)
Dog waste collected from the customer's garden on a recurring schedule.

**Collection frequencies:**
- Weekly
- Fortnightly
- Twice Weekly (Fife customers only — Tuesday and Friday)

**Add-ons (per visit):**
- Sanitisation/Deodorisation: £6 per visit
- Additional dog (beyond 1): £3 per dog per visit

### 2.2 Garden Rescue (one-off deep clean)
A thorough one-off clear of a garden with significant accumulated waste. Priced separately — not in the standard pricing table. Additional info is recorded in the `Deep Clean Additional Info` field.

Garden Rescue customers have `Build Up Flag = true` and `Customer Origin = Garden Rescue`.

---

## 3. Pricing

Base price is set by **garden size** and **collection frequency**. Medium garden weekly is the reference price. Small = −20%. Large = +30%.

| Garden Size | Weekly | Fortnightly |
|-------------|--------|-------------|
| Small       | £16.80 | £19.20      |
| Medium      | £21.00 | £24.00      |
| Large       | £27.30 | £31.20      |

**Add-ons (same for weekly and fortnightly):**
- Additional dog (per extra dog): £3.00 per visit
- Sanitisation/Deodorisation: £6.00 per visit
- First dog is always included in the base price

**Payment frequencies available:** Weekly / Fortnightly / Four Weekly / Monthly

**Payment multipliers** (applied to per-visit rate to calculate invoice amount):

| Collection Frequency | Payment Frequency | Multiplier |
|----------------------|-------------------|------------|
| Weekly               | Weekly            | 1          |
| Weekly               | Fortnightly       | 2          |
| Weekly               | Four Weekly       | 4          |
| Weekly               | Monthly           | 4.33       |
| Fortnightly          | Weekly            | 0.5        |
| Fortnightly          | Fortnightly       | 1          |
| Fortnightly          | Four Weekly       | 2          |
| Fortnightly          | Monthly           | 2.17       |

**Authoritative payment frequency field:** `Preferred Payment Frequency` (field key: `contact.preferred_payment_frequency`). The `Payment Frequency` field (`contact.the_payment_frequency`) is the billing execution field — these should match. If they differ, flag for operator review.

---

## 4. Customer Lifecycle

### Entry Point A — Free Trial (direct sign-up)
1. Customer uses the online calculator on the Scoop Patrol website.
2. Contact is created in GHL. `Customer Origin = Free Trial`. `Trial Stage = Not Started`.
3. First maintenance visit happens. `Trial Stage → Week 1`.
4. Customer converts to paying. Card captured → recurring invoice schedule created. `Trial Stage → Paying Customer`. `service activated` tag added.

### Entry Point B — Garden Rescue
1. Customer books a Garden Rescue via the website calculator.
2. Liam and Liam carry out the deep clean visit. Customer pays after the visit — this puts their card on file.
3. `Build Up Flag = true`. `Customer Origin = Garden Rescue`.
4. Free maintenance trial starts the following week — same flow as Entry Point A from step 3.

**Note:** Goal is to capture card on file earlier in the process (before the visit). Not yet implemented — do not action this change.

### Ongoing
- Mick services regular maintenance customers on their route day.
- Liam and Liam handle new customers, first visits, and Garden Rescues.
- `service activated` tag = scheduling source of truth. If a customer does not have this tag, they will not be serviced regardless of any other field.

---

## 5. Status Fields

### Service Status (`contact.service_status`)
| Value      | Meaning |
|------------|---------|
| `Active`   | Receiving regular service |
| `Paused`   | Service temporarily suspended until `Payment Paused Until` date |
| `Cancelled`| Service ended |

### Trial Stage (`contact.trial_stage`)
| Value            | Meaning |
|------------------|---------|
| `Not Started`    | Signed up, not yet had first visit |
| `Week 1`         | Had first visit, still on trial |
| `Paying Customer`| Card on file, active recurring billing |

### Payment Status (`contact.payment_status`)
Options: `Active` / `Overdue` / `Pending` / `Paused` / `Cancelled`

⚠️ **This field is unreliable.** The payment status sync script is broken. This field is rarely updated manually. Do not rely on it to assess whether a customer is paying. Use GHL invoice schedules and Stripe directly to verify payment status.

---

## 6. Key Tags

| Tag | Meaning |
|-----|---------|
| `service activated` | **Scheduling source of truth.** Customer is active and on Mick's route. Remove this tag = customer stops being serviced. Never remove without operator approval. |
| `free trial` | Customer is on free trial |
| `deep clean` | Customer had or is having a Garden Rescue |
| `add to optimo-route` | Trigger for adding customer to OptimoRoute routing |
| `follow up sequence activated` | Automated follow-up sequence is running |
| `welcome pack notification recieved` / `welcome pack not recieved` | Welcome comms status |
| `bin collection only` | Customer only gets bin/waste collection, no garden visit |
| `commercial contract` | Business/commercial customer — different terms |

---

## 7. Scheduling & Routing

- **Service Day** field stores which day(s) of the week the customer is visited. It is MULTIPLE_OPTIONS — a customer can have more than one day (e.g. Twice Weekly customers have Tuesday and Friday).
- **Fortnightly Service Group** (`Group A` / `Group B`) — no longer used operationally. The `Next Service Date` field is the source of truth for when a fortnightly customer is next due.
- **OptimoRoute** is the routing software Mick uses. Any change to a customer's service day must be updated in both GHL and OptimoRoute.
- **Twice Weekly** service is currently live for Fife customers only (Tuesday and Friday).

---

## 8. Paused Customers

If a customer requests a pause:
1. Set `Service Status = Paused`
2. Set `Payment Paused Until` to the return date
3. Remove `service activated` tag (stops Mick visiting)
4. Create a dated task to: re-add `service activated` tag + set `Service Status = Active` on the return date

Never service a paused customer before their return date.

---

## 9. Cancellations

When a customer wants to cancel:
1. Ask for their reason (no dedicated field yet — record in conversation notes or `Deep Clean Additional Info` temporarily until a cancellation reason field is created)
2. Set `Service Status = Cancelled`
3. Queue `[ACTION]` to remove `service activated` tag — requires operator approval before execution

No minimum notice period. No final visit convention — service stops when the tag is removed.

---

## 10. Billing

Billing runs via GHL invoice schedules linked to Stripe. The `draft_invoice_cron.py` script catches invoices stuck in draft and either auto-charges saved cards or sends payment links.

**Pricing source of truth:** The customer's active GHL invoice schedule is the authoritative record of what they are currently being charged — not the custom fields. Custom fields (garden size, frequency, add-ons) reflect what was set at sign-up and may have drifted. If there is a discrepancy between the custom fields and the invoice, the invoice wins. Always pull the active invoice schedule when answering any question about what a customer is currently paying.

**Card on file:** Captured via Stripe Checkout at point of payment. The Garden Rescue visit payment puts the card on file. Free trial customers have their card captured when they convert.

**Build Up Selection** — captured at sign-up, records how long since the garden was last cleared:
- `within month` / `1_to_3_months` / `3_to_6_months` / `6_plus_months` / `never_cleared`

This affects the Garden Rescue visit complexity but does not change regular maintenance pricing.

**Skip Run:** `Skip Run Requested` checkbox flags a customer requesting a skipped visit. `Skip Run Cost` is filled in after receiving a price via WhatsApp from the route contact. Agent should not set skip run cost — this is a manual flow.

**Long Grass Flag:** Set by Mick during route visits. Options: `No Issue` / `Slightly Long` / `Too Long - Needs Cut` / `Reported to Customer`. Agent reads this field only — never writes to it.

---

## 11. Tone of Voice

- Warm, fun, professional. Imagine a friendly local business owner texting — not a corporate chatbot.
- Never sound like a generic AI response (formal, cold, robotic). If it reads like ChatGPT, rewrite it.
- Use plain English. Scottish context — customers are local, language can reflect that naturally.
- Sign-off for first or formal messages: *"Liam & Liam, Team Scoop Patrol 🐾"*
- Casual follow-ups in ongoing threads do not need the sign-off.
- Tagline you can use naturally: "Always on Doody"
- Reference the dog by name whenever it's in the record. Customers love this.
- Mention Mick when relevant to route/scheduling ("Mick will be with you on Thursday").

**Phrases to use:**
- "We're always here if you need us"
- "Always on Doody"
- "Liam & Liam, Team Scoop Patrol 🐾" (sign-off)

**Never:**
- Sound corporate or salesy
- Use phrases like "I hope this message finds you well"
- Over-explain or be wordy

---

## 12. Team

| Person | Role |
|--------|------|
| Liam D | Owner / operator — primary decision maker |
| Liam W | Owner / operations manager — social media, day-to-day ops |
| Mick   | Driver — handles all regular maintenance routes |

When messaging customers about their regular service, Mick is the person they'll see. When messaging about sign-up, billing, or account changes, it comes from Liam and Liam.

---

## 13. Escalation & Approval Rules

**Everything requires operator approval before execution.** The agent proposes; the operator approves. This applies to all replies and all CRM/billing mutations.

**Red flags — flag prominently in the draft card:**
- Any message with angry or upset tone from the customer
- Requests for refunds
- Threats to leave a review (positive or negative)
- Any mention of a complaint

**Never auto-execute without approval:**
- Removing the `service activated` tag
- Any billing operation (charge, refund, cancel, pause)
- Service day changes (requires OptimoRoute update too)
- Any cancellation action

**Out-of-scope behaviour:** If the agent cannot handle a message with confidence, it must still draft the best possible reply and flag the uncertainty with a `[FLAG]` annotation — never return a blank escalation.

---

## 14. Glossary

| Term | Meaning |
|------|---------|
| Service day | The day(s) of the week a customer is visited |
| Frequency | How often they are visited — weekly, fortnightly, or twice weekly |
| Fortnightly | Every two weeks |
| Four Weekly | Every four weeks (payment option, not collection frequency) |
| Garden Rescue | One-off deep clean of heavily accumulated waste |
| Free trial | New customer period before card is captured and billing starts |
| Build-up | Accumulated waste from before the customer joined |
| service activated tag | The scheduling source of truth — presence = on Mick's route |
| Group A / Group B | Fortnightly week split — no longer operationally used |
| Skip run | A visit that is skipped at customer request |
| Paying Customer | Trial Stage value meaning card on file and billing active |
| Liam and Liam | The two owners — always refer to them together in customer messages |

---

## 15. Fields the Agent Should Never Write Without Approval

| Field | Reason |
|-------|--------|
| `service_activated` tag | Scheduling source of truth |
| `Service Status` | Changing to Cancelled or Paused has immediate operational impact |
| `Payment Status` | Unreliable field — changes here mean nothing without fixing billing |
| `Long Grass Flag` | Mick's operational field — agent reads only |
| `Skip Run Cost` | Set manually after WhatsApp price confirmation |
| Any billing field | All billing mutations require explicit approval |

---

## 16. Missing / To-Do (Known Gaps)

- **Cancellation reason field** does not exist in GHL yet — needs creating
- **Card capture timing** — goal is to capture card before Garden Rescue visit, not after. Not yet implemented.
- **Payment Status sync** — field is broken/unreliable. Do not trust it. Use Stripe and GHL invoice schedules as source of truth for payment status.
