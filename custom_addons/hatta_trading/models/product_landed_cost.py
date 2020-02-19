from odoo import api, fields, models, _
from odoo.exceptions import UserError


class LandedCost(models.Model):
    _name = 'purchase.landed.cost'

    @api.depends('cost_lines')
    def get_total_landed_cost(self):
        for rec in self:
            rec.total_cost = sum([x.amount_lc for x in rec.cost_lines])

    @api.depends('filter_by_product', 'landed_cost_lines')
    def get_filtered_landed_cost_lines(self):
        if self.filter_by_product:
            self.landed_cost_lines_filtered = [
                (6, False,
                 self.landed_cost_lines.filtered(lambda s: s.purchase_order_line.id == self.filter_by_product.id).ids)]
        else:
            self.landed_cost_lines_filtered = self.landed_cost_lines

    name = fields.Char(readonly=True, default='Draft Landed Cost Estimation')

    purchase_order_id = fields.Many2one('purchase.order', required=True, ondelete='cascade')
    cost_sheet_id = fields.Many2one('hatta.cost.sheet', required=True, ondelete='cascade')

    margin = fields.Float('Margin Amount', related='cost_sheet_id.margin')
    margin_split_method = fields.Selection([('equal', 'Equally'), ('quantity', 'By Quantity'),
                                             ('price', 'By Current Price'), ('percentage', 'By Percentage')],
                                            string='Split Method', default='equal')
    margin_percentage = fields.Float('Split Percentage')

    state = fields.Selection([('draft', 'Draft'), ('estimated', 'Estimated'), ('confirm', 'Confirmed')],
                             default='draft', required=True, readonly=True)

    order_line = fields.One2many(related='purchase_order_id.order_line')
    cost_lines = fields.One2many(related='cost_sheet_id.cost_lines')

    landed_cost_lines = fields.One2many('pol.landed.cost.line', 'landed_cost_id')
    landed_cost_lines_filtered = fields.Many2many('pol.landed.cost.line', compute='get_filtered_landed_cost_lines',
                                                  store=False)

    total_cost = fields.Float('Total Landed Cost', compute='get_total_landed_cost')
    filter_by_product = fields.Many2one('purchase.order.line')

    landed_cost_lines_with_percentage = fields.One2many('pol.landed.cost.line', 'landed_cost_id',
                                                        domain=[('split_method', '=', 'percentage')])
    date = fields.Date(string='Date', default=fields.Date.today(), readonly=True,)


    def get_additional_landed_cost(self, order_line, cost_line, totals):
        split_by = cost_line.split_method
        if split_by == 'equal':
            return cost_line.amount_lc / totals['total_lines']
        if split_by == 'quantity':
            return (cost_line.amount_lc / totals['total_qty']) * order_line.product_qty
        if split_by == 'price':
            return (cost_line.amount_lc / totals['total_price']) * order_line.price_total_lc
        if split_by == 'percentage':
            return 0.0

    def get_margin(self, order_line, totals):
        split_by = self.margin_split_method
        margin = self.margin
        if split_by == 'equal':
            return margin / totals['total_lines']
        if split_by == 'quantity':
            return (margin / totals['total_qty']) * order_line.product_qty
        if split_by == 'price':
            return (margin / totals['total_price']) * order_line.price_total_lc
        if split_by == 'percentage':
            return 0.0

    def show_percentage_entering_wizard(self):
        return {
            'name': _("Percentage Distribution Mapping"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_id': self.env.ref('hatta_trading.wizard_percentage_distribution_mapping').id,
            'view_type': 'form',
            'res_model': 'wizard.purchase.landed.cost',
            'context': {'default_landed_cost_id': self.id},
            'target': 'new',
        }

    @api.multi
    def compute(self):
        landed_cost_lines = []
        totals = {
            'total_lines': len(self.order_line),
            'total_qty': sum([x.product_qty for x in self.order_line]),
            'total_price': sum([x.price_total_lc for x in self.order_line])
        }
        has_percentage_method = False
        existing = {}
        removables = self.landed_cost_lines.ids

        for line in self.landed_cost_lines:
            existing.update({(line.purchase_order_line.id, line.cost_sheet_line_id.id): line.id})

        for order_line in self.order_line:
            for cost_line in self.cost_lines:
                additional_landed_cost = self.get_additional_landed_cost(order_line, cost_line, totals)
                if (order_line.id, cost_line.id) in existing:
                    exist_id = existing[(order_line.id, cost_line.id)]
                    removables.remove(exist_id)
                    landed_cost_lines.append((1, exist_id, {
                        'additional_landed_cost': additional_landed_cost
                    }))
                else:
                    landed_cost_lines.append((0, 0, {
                        'purchase_order_line': order_line.id,
                        'cost_sheet_id': self.cost_sheet_id.id,
                        'cost_sheet_line_id': cost_line.id,
                        'additional_landed_cost': additional_landed_cost
                    }))
                if cost_line.split_method == 'percentage':
                    has_percentage_method = True

        for rem in removables:
            landed_cost_lines.append((2, rem))
        self.landed_cost_lines = landed_cost_lines
        if self.margin and self.margin_split_method:
            for line in self.order_line:
                line.dist_margin = self.get_margin(line, totals)
        if not has_percentage_method and self.margin_split_method != 'percentage':
            return
        return self.show_percentage_entering_wizard()

    @api.multi
    def validate_estimation(self):
        if self.cost_lines and not self.landed_cost_lines:
            raise UserError('Please click Compute Button before validating to compute Landed Cost Lines')
        self.check_percentage_distribution()
        self.state = 'estimated'
        self.purchase_order_id.state = 'sale_ready'
        self.name = 'LC-%s' % self.purchase_order_id.name

    def check_percentage_distribution(self):
        for cost in self.landed_cost_lines_with_percentage.mapped('cost_sheet_line_id.id'):
            if sum(self.landed_cost_lines_with_percentage.filtered(
                    lambda s: s.cost_sheet_line_id.id == cost).mapped('applied_percentage')) != 100:
                raise UserError('Please verify the Cost Percentage Allocation. Its not completely allocated.')

        if self.margin_split_method == 'percentage':
            if sum(self.order_line.mapped('margin_percentage')) != 100:
                raise UserError('Please verify the Margin Percentage Allocation. Its not completely allocated.')

    @api.multi
    def confirm(self):
        self.state = 'confirm'

    @api.multi
    def set_to_draft(self):
        pass


class PolLandedCostLine(models.Model):
    _name = 'pol.landed.cost.line'
    _order = 'cost_sheet_line_id'
    _inherits = {'purchase.order.line': 'purchase_order_line'}

    @api.depends('cost_sheet_line_id', 'applied_percentage')
    def compute_name(self):
        for rec in self:
            if rec.applied_percentage:
                rec.name = '%s (%s %s)' % (rec.cost_sheet_line_id.line_charge_id.name, rec.applied_percentage, '%')
            else:
                rec.name = rec.cost_sheet_line_id.line_charge_id.name

    name = fields.Char(compute='compute_name', store=True)

    landed_cost_id = fields.Many2one('purchase.landed.cost', required=True, ondelete='cascade')

    purchase_order_line = fields.Many2one('purchase.order.line', required=True, ondelete='cascade')
    cost_sheet_id = fields.Many2one('hatta.cost.sheet')

    cost_sheet_line_id = fields.Many2one('cost.sheet.line', required=True, string='Cost Line')
    amount = fields.Float(string="Total Line Value", related='cost_sheet_line_id.amount_lc', store=True)
    split_method = fields.Selection(string='Split Method Applied', related='cost_sheet_line_id.split_method',
                                    store=True)
    additional_landed_cost = fields.Float('Additional Landed Cost')

    applied_percentage = fields.Float('Split Percentage')

    def apply_percentage(self):
        for line in self:
            if line.split_method == 'percentage' and line.applied_percentage > 0.0:
                line.additional_landed_cost = line.amount * (line.applied_percentage/100)


