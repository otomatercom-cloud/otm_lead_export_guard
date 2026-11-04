from odoo import fields, models


class OtmLeadExportLog(models.Model):
    _name = 'otm.lead.export.log'
    _description = 'Lead Export Log'
    _order = 'id desc'

    user_id = fields.Many2one('res.users', string='User', readonly=True, index=True)
    date = fields.Datetime(default=fields.Datetime.now, readonly=True)
    model = fields.Char(readonly=True)
    record_count = fields.Integer(string='Records', readonly=True)
    field_count = fields.Integer(string='Fields', readonly=True)
    result = fields.Selection([('allowed', 'Exported'), ('blocked', 'Blocked')],
                              readonly=True, index=True)
