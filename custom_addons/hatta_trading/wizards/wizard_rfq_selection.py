from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.multi
    def toggle_selection(self):
        self.selected_for_sale ^= True
        return self.enquiry_id.action_wizard_rfq_selection()


class RfqSelection(models.Model):
    _inherit = 'enquiry.details'

    @api.depends('bid_html_group_supplier')
    def get_bid_html(self):
        for rec in self:
            rec.bid_html = rec.enquiry_id.bid_html

    selected_rfq_lines = fields.One2many('purchase.order.line', 'enquiry_id', readonly=False,
                                         domain=[('state', '=', 'sale_ready'), ('selected_for_sale', '=', True)])
    unselected_rfq_lines = fields.One2many('purchase.order.line', 'enquiry_id', readonly=False,
                                           domain=[('state', '=', 'sale_ready'), ('selected_for_sale', '=', False)])

    @api.depends('selected_rfq_lines', 'unselected_rfq_lines')
    def get_lines(self):
        self.selected_rfq_lines = self.purchase_order_lines.filtered(lambda s: s.selected_for_sale)
        self.unselected_rfq_lines = self.purchase_order_lines.filtered(lambda s: (not s.selected_for_sale))
