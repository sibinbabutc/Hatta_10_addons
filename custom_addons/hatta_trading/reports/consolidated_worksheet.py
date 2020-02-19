from dateutil.relativedelta import relativedelta
import datetime


from odoo import models, fields, api


class WorksheetReport(models.AbstractModel):
    _name = 'report.hatta_trading.hatta_consolidated_worksheet_report'

    @api.multi
    def render_html(self, docids, data=None):
        worksheet = self.env['enquiry.details'].search([('id', '=', '')])
        docargs = {
            'docs': docids,
        }
        return self.env['report'].render('hatta_trading.hatta_consolidated_worksheet_report', docargs)
