from odoo import api, fields, models


class CoveringLetter(models.TransientModel):
    _name = 'covering.letter'
    _description = 'Covering Letter'

    enquiry_id = fields.Many2one('enquiry.details', string='Enquiry')
    submission_date = fields.Date(string='Submission Date')
    report_type = fields.Selection(string="Report Type", selection=[('commercial', 'Commercial'),
                                                                    ('technical', 'Technical')], default='commercial')
    duty_exemption = fields.Boolean(string='Duty Exemption')
    duty_exemption_letter = fields.Selection(string="Duty Exemption Letter",
                                             selection=[('required', 'Required'), ('not_required', 'Not Required')],
                                             default='')
    revised = fields.Boolean(string='Revised')
    user_format = fields.Boolean(string='User Format')
    note = fields.Char(string='Note')
    add_note = fields.Char(string='Additional Note')
    section_1 = fields.Text(string='Section 1',
                            default='We thank you for your valued enquiry and are pleased to submit our offer as per '
                                    'enclosed.')
    section_2 = fields.Text(string='Section 2',
                            default='In case of any changes in the quantities, please contact us for confirmation of\n'
                                    'validity of prices with our principal supplier/s.\n'
                                    '\n Hope our offer meets your requirements and if any further clarification, '
                                    'we are at your disposal.')

    @api.multi
    def print_covering_letter(self):
        return self.env['report'].get_action(self, 'hatta_trading.hatta_covering_letter')
