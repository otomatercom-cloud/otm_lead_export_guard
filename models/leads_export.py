import logging

from odoo import SUPERUSER_ID, _, api, models
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)
GROUP = 'otm_lead_export_guard.group_lead_export'


class LeadsLogicExportGuard(models.Model):
    _inherit = 'leads.logic'

    @api.model
    def _user_can_export(self):
        user = self.env.user
        return user.id == SUPERUSER_ID or user.has_group(GROUP)

    def _check_can_export(self):
        if not self._user_can_export():
            self._otm_log_export(False, 0)
            raise AccessError(_(
                "Lead export is disabled. Ask the administrator to grant you "
                "'Lead Export Allowed' access."))
        return True

    def _otm_log_export(self, allowed, nfields):
        try:
            with self.pool.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                env['otm.lead.export.log'].create({
                    'user_id': self.env.uid,
                    'model': self._name,
                    'record_count': len(self),
                    'field_count': nfields,
                    'result': 'allowed' if allowed else 'blocked',
                })
        except Exception:
            _logger.exception("Could not write lead export log")

    def export_data(self, fields_to_export):
        allowed = self._user_can_export()
        self._otm_log_export(allowed, len(fields_to_export or []))
        if not allowed:
            raise AccessError(_(
                "Lead export is disabled. Ask the administrator to grant you "
                "'Lead Export Allowed' access."))
        return super().export_data(fields_to_export)
