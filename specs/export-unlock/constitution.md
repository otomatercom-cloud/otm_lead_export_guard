# Constitution - Lead Export Guard
- Odoo 19 only. OPL-1, otm. prefix, author Otomater.
- Import and other ACLs are never touched. Every new model has an ACL row.
- The approval code is never visible to the requester or to admin. Only an approver (not the requester) sees it, once.
- Code is stored as an HMAC hash for checking; the reveal copy is encrypted and wiped on reveal, use, or expiry.
- Real enforcement is server-side; the hidden Export button is only convenience.
- No dependency on outgoing mail (no plaintext code in a mail queue).
- Log writes use their own cursor so they survive a raised error.
- Syntax-check before delivery; state plainly what was not tested on a server.
