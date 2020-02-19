from odoo import api, fields, models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    sub_model = fields.Char()
    
    @api.model
    def create(self, vals):
        if 'sub_model' in vals and vals['sub_model'] == 'enquiry.details':
            vals.update({
                'res_model': vals['sub_model']
            })
        return super(IrAttachment, self).create(vals)