from odoo import api, fields, models


class OtmLeadExportSetting(models.Model):
    _name = 'otm.lead.export.setting'
    _description = 'Lead Export Settings'

    name = fields.Char(default='Lead Export Settings', readonly=True)
    mail_enabled = fields.Boolean(string='Also email the code to approvers', default=True)
    mail_server_id = fields.Many2one('ir.mail_server', string='OTP mail server',
                                     help="Outgoing server used for the approval code mail. Change any time.")
    default_applied = fields.Boolean(readonly=True)

    @api.model
    def get_setting(self):
        cfg = self.env.ref('otm_lead_export_guard.setting_default').sudo()
        if not cfg.mail_server_id and not cfg.default_applied:
            servers = self.env['ir.mail_server'].sudo().search([('active', '=', True)])
            gmail = servers.filtered(lambda s: 'gmail' in (s.smtp_host or '').lower())[:1]
            cfg.write({'mail_server_id': (gmail or servers[:1]).id or False, 'default_applied': True})
        return cfg
