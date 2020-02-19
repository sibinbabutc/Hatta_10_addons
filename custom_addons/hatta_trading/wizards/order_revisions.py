from odoo import api, fields, models, _


class RfqOrderRevision(models.Model):
    _name = 'rfq.order.revision'

    partner_id = fields.Many2one('res.partner', string='Customer', domain=[('supplier', '=', True)])
    revision_reason = fields.Many2one('revision.reason', string='Revision Reason', store=True,
                                      related='order_reference.revision_reason')
    order_reference = fields.Many2one('purchase.order', string='Reference')

    @api.multi
    def submit_rfq_revision(self):
        return self.order_reference.new_revision()


class SaleOrderRevision(models.TransientModel):
    _name = 'sale.order.revision'

    partner_id = fields.Many2one('res.partner', string='Customer', domain=[('customer', '=', True)])
    revision_reason = fields.Many2one('revision.reason', string='Revision Reason', store=True)
    order_reference = fields.Many2one('sale.order', string='Reference')

    @api.multi
    def action_sale_order_revision(self):
        sale_obj = self.env['sale.order'].browse(self.order_reference.id)
        vals = {
            'revision_reason': self.revision_reason.id
        }
        return sale_obj.new_revision(vals)