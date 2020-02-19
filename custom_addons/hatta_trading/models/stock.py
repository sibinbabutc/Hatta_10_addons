from odoo import api, fields, models, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class ProcurementOrder(models.Model):
    _inherit = "procurement.order"

    def _get_stock_move_values(self):
        ''' Returns a dictionary of values that will be used to create a stock move from a procurement.
        This function assumes that the given procurement has a rule (action == 'move') set on it.

        :param procurement: browse record
        :rtype: dictionary
        '''
        group_id = False
        if self.rule_id.group_propagation_option == 'propagate':
            group_id = self.group_id.id
        elif self.rule_id.group_propagation_option == 'fixed':
            group_id = self.rule_id.group_id.id
        date_expected = (datetime.strptime(self.date_planned, DEFAULT_SERVER_DATETIME_FORMAT) - relativedelta(
            days=self.rule_id.delay or 0)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        # it is possible that we've already got some move done, so check for the done qty and create
        # a new move with the correct qty
        qty_done = sum(self.move_ids.filtered(lambda move: move.state == 'done').mapped('product_uom_qty'))
        qty_left = max(self.product_qty - qty_done, 0)
        return {
            'name': self.name[:2000],
            'company_id': self.rule_id.company_id.id or self.rule_id.location_src_id.company_id.id or self.rule_id.location_id.company_id.id or self.company_id.id,
            'product_id': self.product_id.id,
            'serial_num': self.sale_line_id and self.sale_line_id.serial_no,
            'product_uom': self.product_uom.id,
            'product_uom_qty': qty_left,
            'partner_id': self.rule_id.partner_address_id.id or (
                        self.group_id and self.group_id.partner_id.id) or False,
            'location_id': self.rule_id.location_src_id.id,
            'location_dest_id': self.location_id.id,
            'move_dest_id': self.move_dest_id and self.move_dest_id.id or False,
            'procurement_id': self.id,
            'rule_id': self.rule_id.id,
            'procure_method': self.rule_id.procure_method,
            'origin': self.origin,
            'picking_type_id': self.rule_id.picking_type_id.id,
            'group_id': group_id,
            'route_ids': [(4, route.id) for route in self.route_ids],
            'warehouse_id': self.rule_id.propagate_warehouse_id.id or self.rule_id.warehouse_id.id,
            'date': date_expected,
            'date_expected': date_expected,
            'propagate': self.rule_id.propagate,
            'priority': self.priority,
        }


class StockMove(models.Model):
    _inherit = 'stock.move'

    serial_num = fields.Char('Sl No.')


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    package = fields.Char('Package')
    return_note = fields.Text("Return Note")
    show_return_note = fields.Boolean("", )

    @api.multi
    def find_lpo_numbers(self):
        po_lines = self.sale_id.enquiry_id.selected_purchase_order_lines.mapped('order_id')
        name = ""
        i = 0
        for item in po_lines:
            if i > 0:
                name += ','
            name += item.name
        return name


class StockReturnPickingInherit(models.TransientModel):
    _inherit = 'stock.return.picking'

    return_note = fields.Text("Return Note")

    @api.multi
    def create_returns(self):
        for wizard in self:
            new_picking_id, pick_type_id = wizard._create_returns()
            picking_obj = self.env['stock.picking'].browse(new_picking_id)
            picking_obj.return_note = wizard.return_note
            picking_obj.show_return_note = True
        # Override the context to disable all the potential filters that could have been set previously
        ctx = dict(self.env.context)
        ctx.update({
            'search_default_picking_type_id': pick_type_id,
            'search_default_draft': False,
            'search_default_assigned': False,
            'search_default_confirmed': False,
            'search_default_ready': False,
            'search_default_late': False,
            'search_default_available': False,
        })
        return {
            'name': _('Returned Picking'),
            'view_type': 'form',
            'view_mode': 'form,tree,calendar',
            'res_model': 'stock.picking',
            'res_id': new_picking_id,
            'type': 'ir.actions.act_window',
            'context': ctx,
        }
