from odoo import api, fields, models

APPROVER_GROUP = 'otm_lead_export_guard.group_export_approver'


class OtmLeadExportApprover(models.Model):
    _name = 'otm.lead.export.approver'
    _description = 'Lead Export Approver'

    name = fields.Char(related='user_id.name', store=True)
    user_id = fields.Many2one('res.users', string='Approver (Director)', required=True,
                              domain=[('share', '=', False)], ondelete='cascade')
    active = fields.Boolean(default=True)

    _sql_constraints = [('user_uniq', 'unique(user_id)', 'This user is already an approver.')]

    def _sync_group(self, users, add):
        grp = self.env.ref(APPROVER_GROUP)
        for user in users.sudo():
            if not add:
                # keep the group while another active approver row remains
                if self.sudo().search_count([('user_id', '=', user.id), ('active', '=', True)]):
                    continue
            user.write({'group_ids': [(4 if add else 3, grp.id)]})

    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        self._sync_group(recs.filtered('active').mapped('user_id'), True)
        return recs

    def write(self, vals):
        old = self.mapped('user_id')
        res = super().write(vals)
        self._sync_group(self.filtered('active').mapped('user_id'), True)
        self._sync_group((old | self.mapped('user_id')) - self.filtered('active').mapped('user_id'), False)
        return res

    def unlink(self):
        users = self.mapped('user_id')
        res = super().unlink()
        self._sync_group(users, False)
        return res
