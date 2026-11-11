# Plan
- Models: otm.lead.export.approver (user_id, active; syncs the Lead Export Approver group), otm.lead.export.request (hash + encrypted reveal copy, state, expiry, attempts, unlocked_until, revealed_by), wizards (request, unlock), extended log.
- Code: 6 digits via secrets; HMAC-SHA256 hash (key database.secret, message "<id>:<code>"); reveal copy Fernet-encrypted (key derived from database.secret), wiped on reveal/use/expiry.
- Reveal: Approvals list button -> sticky notification to that approver only (no DB row for the plaintext).
- Enforcement: leads.logic _user_can_export / _check_can_export / export_data: uid==SUPERUSER or (in Lead Export Allowed group AND an approved request with unlocked_until > now).
- Wrong code returns a notification (no raise) so the attempt counter commits.
- Cron every minute expires codes and windows.
- Security: global record rule (own requests; admin and approvers see all). Menu root visible to admin, allowed group, approvers.
- Risk: stale access cache after install -> restart the service.
