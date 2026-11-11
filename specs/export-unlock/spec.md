# Spec - Code-approved temporary export
Problem: lead export is blocked for everyone, with a controlled, audited, temporary exception.

## User stories and acceptance
1. Admin grants "Lead Export Allowed" so the user sees Export. Without a code, export still fails.
2. User requests export: reason required, window 5/10/15/20/30 min (max 30).
3. An approver (Director list, not the requester) sees pending requests under Lead Export > Approvals and clicks "Show code"; the code appears once.
4. Requester enters the code: valid 10 min, one-time, 3 wrong attempts lock the request, a new request expires the previous one.
5. After success the user can export only for the chosen minutes, then it is blocked again.
6. Admin without a code is blocked. Import is unaffected.
7. Every step is logged: requested, code shown, unlocked, wrong code, locked, expired, exported, blocked.

## Out of scope
Email delivery, per-export count limits, file watermarking.

## Open questions (assumptions taken)
- Approvers are Odoo users listed under Lead Export > Approvers (assumed).
- The Director tells the code to the user by call/WhatsApp (assumed).
