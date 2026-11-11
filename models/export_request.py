import base64
import hashlib
import hmac
import secrets
import logging
from datetime import timedelta

from cryptography.fernet import Fernet, InvalidToken

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

CODE_VALID_MINUTES = 10
MAX_ATTEMPTS = 3
WINDOW_CHOICES = [('5', '5 minutes'), ('10', '10 minutes'), ('15', '15 minutes'),
                  ('20', '20 minutes'), ('30', '30 minutes')]


_logger = logging.getLogger(__name__)


def _notify(message, kind='success', close=False):
    params = {'message': message, 'type': kind, 'sticky': False}
    if close:
        params['next'] = {'type': 'ir.actions.act_window_close'}
    return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': params}


class OtmLeadExportRequest(models.Model):
    _name = 'otm.lead.export.request'
    _description = 'Lead Export Request'
    _order = 'id desc'

    user_id = fields.Many2one('res.users', string='Requested by', required=True,
                              readonly=True, index=True)
    reason = fields.Text(required=True, readonly=True)
    minutes = fields.Selection(WINDOW_CHOICES, string='Window', required=True, readonly=True)
    state = fields.Selection([
        ('sent', 'Code sent'), ('approved', 'Unlocked'), ('expired', 'Expired'),
        ('locked', 'Locked')], default='sent', readonly=True, index=True)
    code_hash = fields.Char(readonly=True, groups='base.group_system')
    code_expiry = fields.Datetime(readonly=True)
    attempts = fields.Integer(readonly=True)
    unlocked_until = fields.Datetime(string='Export allowed until', readonly=True)
    code_enc = fields.Char(readonly=True, groups='base.group_system', prefetch=False)
    revealed_by = fields.Many2one('res.users', string='Code shown to', readonly=True)

    # ---- code helpers -------------------------------------------------
    def _hash(self, code):
        secret = self.env['ir.config_parameter'].sudo().get_param('database.secret') or ''
        return hmac.new(secret.encode(), f'{self.id}:{code}'.encode(), hashlib.sha256).hexdigest()

    def _fernet(self):
        secret = self.env['ir.config_parameter'].sudo().get_param('database.secret') or ''
        return Fernet(base64.urlsafe_b64encode(hashlib.sha256(('enc' + secret).encode()).digest()))

    @api.model
    def _active_unlock(self, user):
        return self.sudo().search([
            ('user_id', '=', user.id), ('state', '=', 'approved'),
            ('unlocked_until', '>', fields.Datetime.now())], limit=1)

    # ---- user actions -------------------------------------------------
    @api.model
    def create_and_send(self, reason, minutes):
        user = self.env.user
        approvers = self.env['otm.lead.export.approver'].sudo().search(
            [('active', '=', True), ('user_id', '!=', user.id)])
        if not approvers:
            raise UserError(_("No approver is configured. Ask the administrator to add a Director under Lead Export > Approvers."))
        self.sudo().search([('user_id', '=', user.id), ('state', '=', 'sent')]).write({'state': 'expired'})
        req = self.sudo().create({
            'user_id': user.id, 'reason': reason, 'minutes': minutes,
            'code_expiry': fields.Datetime.now() + timedelta(minutes=CODE_VALID_MINUTES),
        })
        code = f'{secrets.randbelow(10 ** 6):06d}'
        req.write({'code_hash': req._hash(code),
                   'code_enc': req._fernet().encrypt(code.encode()).decode()})
        mail_status = req._send_code_mail(code, approvers)
        self.env['otm.lead.export.log'].log_event(
            'requested', user_id=user.id, note=f"{(reason or '')[:150]} | mail: {mail_status}")
        return req

    def _send_code_mail(self, code, approvers):
        """Optional mail copy of the code. The mail record is deleted right after sending,
        so the code never stays in the mail queue. Never raises."""
        self.ensure_one()
        cfg = self.env['otm.lead.export.setting'].get_setting()
        if not cfg.mail_enabled or not cfg.mail_server_id:
            return 'off'
        emails = [e for e in approvers.mapped('user_id.partner_id.email') if e]
        if not emails:
            return 'no approver email'
        server = cfg.mail_server_id
        sender = server.from_filter if server.from_filter and '@' in server.from_filter else (
            server.smtp_user if '@' in (server.smtp_user or '') else self.env.company.email)
        reason = (self.reason or '').replace('<', '&lt;')
        body = _(
            "<p><b>%(user)s</b> has asked to export lead data.</p>"
            "<p>Reason: %(reason)s<br/>Export window: %(minutes)s minutes</p>"
            "<p>Approval code: <b style='font-size:20px;letter-spacing:3px'>%(code)s</b></p>"
            "<p>Share this code with the user only if you approve. "
            "It is valid for %(valid)s minutes and works once.</p>",
            user=self.user_id.name, reason=reason, minutes=self.minutes,
            code=code, valid=CODE_VALID_MINUTES)
        mail = False
        status = 'failed'
        to = ', '.join(emails)
        try:
            mail = self.env['mail.mail'].sudo().create({
                'subject': _("Lead export approval code - %s", self.user_id.name),
                'body_html': body, 'email_to': to,
                'email_from': sender, 'mail_server_id': server.id, 'auto_delete': False,
            })
            mail.send(raise_exception=False)
            mail.invalidate_recordset(['state', 'failure_reason'])
            if mail.state == 'sent':
                status = f'sent to {to}'
            else:
                status = f'failed ({mail.state}) to {to}: {(mail.failure_reason or "no reason")[:150]}'
        except Exception as exc:
            _logger.exception("Lead export code mail failed")
            status = f'failed to {to}: {str(exc)[:150]}'
        finally:
            try:
                if mail:
                    mail.unlink()
            except Exception:
                _logger.exception("Could not delete code mail")
        return status

    def action_show_code(self):
        """Approver-only: show the code once, then wipe it."""
        self.ensure_one()
        req = self.sudo()
        user = self.env.user
        log = self.env['otm.lead.export.log'].log_event
        is_approver = self.env['otm.lead.export.approver'].sudo().search_count(
            [('user_id', '=', user.id), ('active', '=', True)])
        if not is_approver or req.user_id == user:
            raise AccessError(_("Only an approver other than the requester can see this code."))
        if req.state != 'sent' or not req.code_enc or fields.Datetime.now() > req.code_expiry:
            return _notify(_("This code is no longer available. Ask the user to send a new request."), 'warning')
        try:
            code = req._fernet().decrypt(req.code_enc.encode()).decode()
        except InvalidToken:
            return _notify(_("The code could not be read. Ask the user to send a new request."), 'danger')
        req.write({'code_enc': False, 'revealed_by': user.id})
        log('revealed', user_id=user.id, note=_("Code shown to approver for %s", req.user_id.name))
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {
            'title': _("Code for %s", req.user_id.name),
            'message': _("%(code)s  - tell this code to %(user)s only. It is shown once and valid for %(m)s minutes.",
                         code=code, user=req.user_id.name, m=CODE_VALID_MINUTES),
            'type': 'warning', 'sticky': True}}

    def action_open_unlock(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _("Enter approval code"),
            'res_model': 'otm.lead.export.unlock.wizard', 'view_mode': 'form',
            'target': 'new', 'context': {'default_request_id': self.id},
        }

    def verify_code(self, code):
        self.ensure_one()
        req = self.sudo()
        user = self.env.user
        if req.user_id != user:
            raise AccessError(_("This request belongs to another user."))
        log = self.env['otm.lead.export.log'].log_event
        if req.state != 'sent':
            return _notify(_("This request is no longer open. Please request a new code."), 'warning')
        if fields.Datetime.now() > req.code_expiry:
            req.state = 'expired'
            log('expired', user_id=user.id, note=_("Code expired"))
            return _notify(_("The code has expired. Please request a new one."), 'warning', True)
        if hmac.compare_digest(req.code_hash or '', req._hash((code or '').strip())):
            until = fields.Datetime.now() + timedelta(minutes=int(req.minutes))
            req.write({'state': 'approved', 'unlocked_until': until, 'code_enc': False})
            log('unlocked', user_id=user.id, note=_("Export open for %s minutes", req.minutes))
            return _notify(_("Export unlocked for %s minutes. Refresh the page and export now.",
                             req.minutes), 'success', True)
        req.attempts += 1
        if req.attempts >= MAX_ATTEMPTS:
            req.state = 'locked'
            log('locked', user_id=user.id, note=_("Too many wrong codes"))
            return _notify(_("Too many wrong codes. This request is locked. Request a new code."),
                           'danger', True)
        log('failed', user_id=user.id, note=_("Wrong code (%s)", req.attempts))
        return _notify(_("Wrong code. %s attempt(s) left.", MAX_ATTEMPTS - req.attempts), 'danger')

    @api.model
    def _cron_expire(self):
        now = fields.Datetime.now()
        self.search([('state', '=', 'sent'), ('code_expiry', '<', now)]).write({'state': 'expired', 'code_enc': False})
        self.search([('state', '=', 'approved'), ('unlocked_until', '<', now)]).write({'state': 'expired'})


class OtmLeadExportRequestWizard(models.TransientModel):
    _name = 'otm.lead.export.request.wizard'
    _description = 'Request Lead Export'

    reason = fields.Text(required=True, help="Why do you need this export?")
    minutes = fields.Selection(WINDOW_CHOICES, string='Export window', default='15', required=True)

    def action_send(self):
        self.ensure_one()
        req = self.env['otm.lead.export.request'].create_and_send(self.reason, self.minutes)
        return req.action_open_unlock()


class OtmLeadExportUnlockWizard(models.TransientModel):
    _name = 'otm.lead.export.unlock.wizard'
    _description = 'Enter Lead Export Code'

    request_id = fields.Many2one('otm.lead.export.request', required=True, readonly=True)
    code = fields.Char(string='Approval code')

    def action_unlock(self):
        self.ensure_one()
        if not (self.code or '').strip():
            return _notify(_("Enter the 6-digit code first."), 'warning')
        result = self.request_id.verify_code(self.code)
        self.code = False
        return result
