from odoo import api, fields, models, _
from odoo.exceptions import UserError


class LandedCostPercentageMappingWizard(models.TransientModel):

    _name = 'wizard.purchase.landed.cost'
    _inherits = {'purchase.landed.cost': 'landed_cost_id'}

    landed_cost_id = fields.Many2one('purchase.landed.cost', required=True, ondelete='cascade')

    percentage_mapping_html = fields.Html(compute='get_percentage_mapping_html')

    margin_percentage_mapping_html = fields.Html(compute='get_margin_percentage_mapping_html')

    @api.depends('order_line.margin_percentage')
    def get_margin_percentage_mapping_html(self):
        for rec in self:
            rec.margin_percentage_mapping_html = self.env['ir.qweb'].render(
                'hatta_trading.margin_percentage_mapping_status', {
                    'allocated_margin_percentage': sum(rec.order_line.mapped('margin_percentage'))
                })

    @api.depends('landed_cost_lines_with_percentage.applied_percentage')
    def get_percentage_mapping_html(self):
        for rec in self:
            lines = []
            for cost in rec.landed_cost_lines_with_percentage.mapped('cost_sheet_line_id'):
                lines.append({
                    'cost_line': cost.line_charge_id.name,
                    'allocated_percentage': sum([x.applied_percentage for x in rec.landed_cost_lines_with_percentage
                                                 if x.cost_sheet_line_id.id == cost.id])})
            rec.percentage_mapping_html = self.env['ir.qweb'].render('hatta_trading.percentage_mapping_status', {
                'lines': lines,
                'allocated_margin_percentage': sum(rec.order_line.mapped('margin_percentage'))
            })

    @api.multi
    def complete(self):
        self.landed_cost_id.check_percentage_distribution()
        self.landed_cost_lines_with_percentage.apply_percentage()
        self.order_line.apply_margin_percentage(self.margin)