from odoo import api, fields, models


class ShipInsurance(models.TransientModel):
    _name = 'shipment.insurance'

    date_from = fields.Date('Date From')
    date_to = fields.Date('Date To')
    carrier_id = fields.Char('Carrier')

    @api.multi
    def print_report(self, vals):

        return self.env["report"].get_action(self, 'hatta_reports.insurance.xlsx')





