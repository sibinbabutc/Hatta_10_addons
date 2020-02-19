from odoo import api, fields, models


class ResPartnerInherit(models.Model):
    _inherit = 'res.partner'

    tax_state = fields.Selection(string="Tax Applicable Emirate", selection=[('Abu Dhabi', 'Abu Dhabi'), ('Ajman', 'Ajman'),
                                                       ('Dubai', 'Dubai'), ('Fujairah', 'Fujairah'),
                                                       ('Rasalkhaima', 'Rasalkhaima'), ('Sharjah', 'Sharjah'),
                                                       ('Ummulkuin', 'Ummulkuin')])
