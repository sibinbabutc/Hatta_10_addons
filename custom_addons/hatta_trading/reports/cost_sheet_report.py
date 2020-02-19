from odoo import models, fields, api


class CostSheetReport(models.AbstractModel):
    _name = 'report.hatta_trading.hatta_cost_sheet_report'

    @api.multi
    def render_html(self, docids, data=None):
        docs = self.env['hatta.cost.sheet'].search([('id', 'in', docids)])
        cost_sheets = [{'cs': doc, 'data': doc.compute_all_costs(), 'certificates': doc.cost_line_equipment_ids.filtered(lambda s: s.line_charge_id.related_certificate_id)} for doc in docs]
        res = self.env['report'].render('hatta_trading.hatta_cost_sheet_report', {'cost_sheets': cost_sheets})
        return res