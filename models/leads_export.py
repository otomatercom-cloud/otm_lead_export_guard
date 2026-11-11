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
        if user.id == SUPERUSER_ID:
            return True
        # Layer 1: admin permission. Layer 2: an approved, unexpired code.
        return bool(user.has_group(GROUP) and self.env['otm.lead.export.request']._active_unlock(user))

    def _check_can_export(self):
        if not self._user_can_export():
            self._otm_log_export(False, 0)
            raise AccessError(_(
                "Lead export is locked. Open Lead Export > Request Export "
                "and enter the Director's approval code."))
        return True

    def _otm_log_export(self, allowed, nfields):
        self.env['otm.lead.export.log'].log_event(
            'allowed' if allowed else 'blocked', model=self._name,
            records=len(self), nfields=nfields)

    def export_data(self, fields_to_export):
        allowed = self._user_can_export()
        self._otm_log_export(allowed, len(fields_to_export or []))
        if not allowed:
            raise AccessError(_(
                "Lead export is locked. Open Lead Export > Request Export "
                "and enter the Director's approval code."))
        return super().export_data(fields_to_export)
