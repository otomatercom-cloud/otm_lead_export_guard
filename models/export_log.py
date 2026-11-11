import logging

from odoo import SUPERUSER_ID, api, fields, models

_logger = logging.getLogger(__name__)


class OtmLeadExportLog(models.Model):
    _name = 'otm.lead.export.log'
    _description = 'Lead Export Log'
    _order = 'id desc'

    user_id = fields.Many2one('res.users', string='User', readonly=True, index=True)
    date = fields.Datetime(default=fields.Datetime.now, readonly=True)
    model = fields.Char(readonly=True)
    record_count = fields.Integer(string='Records', readonly=True)
    field_count = fields.Integer(string='Fields', readonly=True)
    note = fields.Char(readonly=True)
    result = fields.Selection([
        ('allowed', 'Exported'),
        ('blocked', 'Blocked'),
        ('requested', 'Code requested'),
        ('revealed', 'Code shown to approver'),
        ('unlocked', 'Unlocked by code'),
        ('failed', 'Wrong code'),
        ('locked', 'Request locked'),
        ('expired', 'Expired'),
    ], readonly=True, index=True)

    @api.model
    def log_event(self, result, user_id=None, model=None, records=0, nfields=0, note=None):
        """Write a log row in its own transaction so it survives a raised error."""
        try:
            with self.pool.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                env['otm.lead.export.log'].create({
                    'user_id': user_id or self.env.uid,
                    'model': model,
                    'record_count': records,
                    'field_count': nfields,
                    'note': note,
                    'result': result,
                })
        except Exception:
            _logger.exception("Could not write lead export log")
