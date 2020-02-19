from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    enquiry_id = fields.One2many('enquiry.details', 'crm_lead_id')
    enquiry_reference = fields.Char(related='enquiry_id.reference')
    enquiry_state = fields.Selection(related='enquiry_id.state')

    @api.multi
    def go_to_enquiries(self):
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_id': self.env.ref('hatta_trading.view_enquiry_details_form').id,
            'view_type': 'form',
            'res_id': self.enquiry_id.id,
            'res_model': 'enquiry.details',
            'target': 'current',
        }

    @api.multi
    def write(self, vals):
        if vals.get('stage_id'):
            if vals['stage_id'] != self._default_stage_id() and not self.enquiry_id:
                raise ValidationError('Please create an Enquiry before making this move.!')
        return super(CrmLead, self).write(vals)