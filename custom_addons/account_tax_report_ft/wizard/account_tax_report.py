from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
import xlwt, xlsxwriter
import codecs, base64

fs = fields.Date.from_string
ts = fields.Date.to_string
from datetime import datetime


class AccountTaxInherit(models.Model):
    _inherit = 'account.tax'

    is_standard_rated = fields.Boolean("Is Standard Rated", )
    is_reverse_charge = fields.Boolean("Is Reverse Charge Applicable", )


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    serial_no = fields.Char(string='Sl.No')
    inv_date = fields.Date(string="Invoice Date", related='invoice_id.date')
    line_tax_amount = fields.Float(compute='_compute_tax_line_price', string='VAT Amount', store=True)
    total_excluded_amount = fields.Float(compute='_compute_tax_line_price', string="Total excluded", store=True)
    total_included_amount = fields.Float(compute='_compute_tax_line_price', string="Total Included", store=True)

    # todo only applicable for tax with single line need to find a solution
    tax_id_for_report = fields.Many2one("account.tax", string="Tax", compute='_compute_tax_line_price', store=True)

    @api.depends('invoice_line_tax_ids', 'price_unit')
    def _compute_tax_line_price(self):
        for record in self:
            currency = record.invoice_id and record.invoice_id.currency_id or None
            price = record.price_unit * (1 - (record.discount or 0.0) / 100.0)
            taxes = False
            tax_amount = 0.0
            if record.invoice_line_tax_ids:
                taxes = record.invoice_line_tax_ids.compute_all(price, currency, record.quantity,
                                                                product=record.product_id,
                                                                partner=record.invoice_id.partner_id)
                record.tax_id_for_report = record.invoice_line_tax_ids.ids[0]
            if taxes:
                for item in taxes['taxes']:
                    tax_amount += item['amount']
                record.total_excluded_amount = taxes['total_excluded']
                record.total_included_amount = taxes['total_included']
            record.line_tax_amount = tax_amount


# class ResPartner(models.Model):
#     _inherit = 'res.partner'
#
#     trn_code = fields.Char(string="TRN")


class AccountInvoiceTax(models.Model):
    _inherit = 'account.invoice.tax'

    inv_date = fields.Date(string="Invoice Date", related='invoice_id.date')


class TaxReport(models.TransientModel):
    _name = 'taxinout.report.wizard'
    _description = 'Report Wizard for tax in and out'

    # target_move = fields.Selection(string="Target Moves", selection=[('posted', 'All Posted Entries'),
    #                                                                  ('all', 'All Entries'), ])
    report_type = fields.Selection(string="Type", selection=[('sale', 'Tax Payable'),
                                                             ('purchase', 'Tax Paid'),
                                                             ('all', 'Both')], default='all')
    # display_details = fields.Boolean("Display Details")
    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)
    tax_filter = fields.Boolean("Filter Tax", )
    taxes = fields.Many2many("account.tax", string="Taxes")
    customers = fields.Many2many('res.partner', 'res_partner_taxinout_customer_rel', 'wizid', 'part_id',
                                 domain="[('customer','=','True')]", string="Customers")
    suppliers = fields.Many2many('res.partner', 'res_partner_taxinout_vendor_rel', 'wizid', 'part_id',
                                 domain="[('supplier','=','True')]", string="Suppliers")

    @api.multi
    def print_report(self):
        return self.env['report'].get_action(self, 'account_tax_report_ft.report_tax_in_out_statement',
                                             data={
                                                 'report_type': self.report_type,
                                                 'from_date': self.start_date,
                                                 'to_date': self.end_date,
                                                 'tax_filter': self.tax_filter,
                                                 'taxes': self.taxes.ids,
                                                 'customers': self.customers.ids,
                                                 'suppliers': self.suppliers.ids,
                                             })

    @api.multi
    def print_report_xls(self):
        tax_ids = []
        tax_id = []
        if not self.tax_filter:
            for tax in self.env['account.tax'].search([]):
                tax_ids.append(tax)
                tax_id.append(tax.id)
        else:
            tax_items = self.env['account.tax'].browse(self.taxes.ids)
            for item in tax_items:
                tax_ids.append(item)
                tax_id.append(item.id)
        domain = [('invoice_line_tax_ids', 'in', tax_id)]
        partners = []
        non_tax_domain = [('invoice_line_tax_ids', '=', False)]
        if self.report_type != 'purchase' and self.customers:
            for item in self.customers:
                partners.append(item.id)
        if self.report_type != 'sale' and self.suppliers:
            for item in self.suppliers:
                partners.append(item.id)
        if partners:
            domain.append(('partner_id', 'in', partners))
            non_tax_domain.append(('partner_id', 'in', partners))
        if self.start_date:
            fd = self.start_date
            domain.append(('invoice_id.date_invoice', '>=', fd))
            non_tax_domain.append(('invoice_id.date_invoice', '>=', fd))
        if self.end_date:
            td = self.end_date
            domain.append(('invoice_id.date_invoice', '<=', td))
            non_tax_domain.append(('invoice_id.date_invoice', '<=', td))
        invoice_line_ids = self.env['account.invoice.line'].search(domain, order='inv_date asc')
        non_tax_inv_lines = self.env['account.invoice.line'].search(non_tax_domain, order='inv_date asc')
        sale_tax_item = invoice_line_ids.filtered(lambda s: s.invoice_id.type == 'out_invoice')
        purchase_tax_item = invoice_line_ids.filtered(lambda s: s.invoice_id.type == 'in_invoice')
        if not sale_tax_item and not purchase_tax_item:
            raise UserError(_('There is no VAT Entries For The Selected Items'))
        non_tax_total_amount = sum(
            (inv_lines.price_subtotal - inv_lines.discount) for inv_lines in non_tax_inv_lines) if non_tax_inv_lines else 0.0
        workbook = xlwt.Workbook()

        # Style for Excel Report
        style0 = xlwt.easyxf(
            'font: bold on; align: vert centre, horiz left;',
            num_format_str='#,##0.00')

        style_data = xlwt.easyxf(
            'align: vert centre, horiz left;',
            num_format_str='#,##0.00')
        styletitle0 = xlwt.easyxf(
            'font: bold on; align: vert centre, horiz centre;',
            num_format_str='#,##0.00')
        sheet = workbook.add_sheet("Tax Report")
        row = 3
        if self.report_type in ['sale', 'all']:
            sheet.write_merge(0, 1, 0, 15, 'Tax Received.(OuTPut VAT)', styletitle0)
            sheet.write(row, 0, 'Place of Supply', style0)
            sheet.write(row, 1, 'Customer', style0)
            sheet.write(row, 2, 'VAT NO', style0)
            sheet.write(row, 3, 'INVOICE NO', style0)
            sheet.write(row, 4, 'Invoice Date', style0)
            sheet.write(row, 5, 'Item', style0)
            sheet.write(row, 6, 'DESCRIPTION', style0)
            sheet.write(row, 7, 'QTY', style0)
            sheet.write(row, 8, 'UNIT', style0)
            sheet.write(row, 9, 'UNIT PRICE', style0)
            sheet.write(row, 10, 'AMOUNT ', style0)
            sheet.write(row, 11, 'DISCOUNT', style0)
            sheet.write(row, 12, 'GROSS AMOUNT BEFORE VAT ', style0)
            sheet.write(row, 13, 'VAT', style0)
            sheet.write(row, 14, 'VAT AMOUNT', style0)
            sheet.write(row, 15, 'AMOUNT  With VAT', style0)
            row += 2
            col = 0
            invoice_ids = sale_tax_item.mapped('invoice_id')
            total_qty = 0.0
            total_amount = 0.0
            total_discount = 0.0
            total_gross_before_vat = 0.0
            vat_total = 0.0
            total_vat_amount = 0.0
            total_amount_with_vat = 0.0
            sale_tax_total = {
                'Abu Dhabi': [0.0, 0.0],
                'Ajman': [0.0, 0.0],
                'Dubai': [0.0, 0.0],
                'Fujairah': [0.0, 0.0],
                'Rasalkhaima': [0.0, 0.0],
                'Sharjah': [0.0, 0.0],
                'Ummulkuin': [0.0, 0.0],
            }
            zero_rated_sale_total = 0.0
            zero_rated_sale_total_vat = 0.0
            for inv in invoice_ids:
                invoice = sale_tax_item.filtered(lambda s: s.invoice_id.id == inv.id)
                col_len = len(invoice) - 1
                palace_of_supply = inv.partner_id.tax_state if inv.partner_id.tax_state else inv.partner_id.state_id.name if inv.partner_id.state_id else 'Unknown'
                sheet.write_merge(row, row + col_len, 0, 0, palace_of_supply, style_data)
                sheet.write_merge(row, row + col_len, 1, 1, inv.partner_id.name, style_data)
                sheet.write_merge(row, row + col_len, 2, 2, inv.partner_id.vat if inv.partner_id.vat else " ", style_data)
                sheet.write_merge(row, row + col_len, 3, 3, inv.number, style_data)
                sheet.write_merge(row, row + col_len, 4, 4, inv.date, style_data)
                x = 1
                for item in invoice:
                    sheet.write(row, 5, str(x), style_data)
                    sheet.write(row, 6, item.product_id.name, style_data)
                    sheet.write(row, 7, item.quantity, style_data)
                    sheet.write(row, 8, item.uom_id.name, style_data)
                    sheet.write(row, 9, item.price_unit, style_data)
                    sheet.write(row, 10, item.price_subtotal, style_data)
                    sheet.write(row, 11, item.discount, style_data)
                    sheet.write(row, 12, item.price_subtotal - item.discount, style_data)
                    sheet.write(row, 13, item.tax_id_for_report.amount, style_data)
                    sheet.write(row, 14, item.line_tax_amount, style_data)
                    sheet.write(row, 15, item.line_tax_amount + item.total_excluded_amount, style_data)
                    total_qty += item.quantity
                    total_amount += item.price_subtotal
                    total_discount += item.discount
                    total_gross_before_vat += item.price_subtotal - item.discount
                    vat_total += item.tax_id_for_report.amount
                    total_vat_amount += item.line_tax_amount
                    total_amount_with_vat += item.line_tax_amount + item.total_excluded_amount
                    if item.tax_id_for_report.is_standard_rated and inv.partner_id.tax_state in sale_tax_total:
                        sale_tax_total[inv.partner_id.tax_state][0] += item.line_tax_amount
                        sale_tax_total[inv.partner_id.tax_state][1] += item.total_excluded_amount
                    if int(item.tax_id_for_report.amount) == 0:
                        zero_rated_sale_total += item.total_excluded_amount
                        zero_rated_sale_total_vat += item.line_tax_amount
                    row += 1
                    x += 1
            row += 1
            sheet.write(row, 5, "Total", style0)
            sheet.write(row, 7, total_qty, style0)
            sheet.write(row, 10, total_amount, style0)
            sheet.write(row, 11, total_discount, style0)
            sheet.write(row, 12, total_gross_before_vat, style0)
            sheet.write(row, 13, vat_total, style0)
            sheet.write(row, 14, total_vat_amount, style0)
            sheet.write(row, 15, total_amount_with_vat, style0)
            row += 3
        if self.report_type in ['purchase', 'all']:
            sheet.write_merge(row, row, 0, 15, 'INPUT VAT (Tax paid)', styletitle0)
            row += 3
            sheet.write(row, 0, 'Place of Supply', style0)
            sheet.write(row, 1, 'Customer', style0)
            sheet.write(row, 2, 'VAT NO', style0)
            sheet.write(row, 3, 'INVOICE NO', style0)
            sheet.write(row, 4, 'Invoice Date', style0)
            sheet.write(row, 5, 'Item', style0)
            sheet.write(row, 6, 'DESCRIPTION', style0)
            sheet.write(row, 7, 'QTY', style0)
            sheet.write(row, 8, 'UNIT', style0)
            sheet.write(row, 9, 'UNIT PRICE', style0)
            sheet.write(row, 10, 'AMOUNT ', style0)
            sheet.write(row, 11, 'DISCOUNT', style0)
            sheet.write(row, 12, 'GROSS AMOUNT BEFORE VAT ', style0)
            sheet.write(row, 13, 'VAT', style0)
            sheet.write(row, 14, 'VAT AMOUNT', style0)
            sheet.write(row, 15, 'AMOUNT  With VAT', style0)
            row += 2
            col = 0
            vendor_bill_ids = purchase_tax_item.mapped('invoice_id')
            v_total_qty = 0.0
            v_total_amount = 0.0
            v_total_discount = 0.0
            v_total_gross_before_vat = 0.0
            v_vat_total = 0.0
            v_total_vat_amount = 0.0
            v_total_amount_with_vat = 0.0
            reverse_rated_purchase_total = 0.0
            reverse_rated_purchase_total_vat = 0.0
            purchase_tax_total_vat = 0.0
            purchase_tax_total_ex_amount = 0.0
            for bills in vendor_bill_ids:
                vendor_bills = purchase_tax_item.filtered(lambda s: s.invoice_id.id == bills.id)
                col_len = len(vendor_bills) - 1

                # sheet.merge_range('B5:E7',"xyz")
                palace_of_supply = bills.partner_id.tax_state if bills.partner_id.tax_state else bills.partner_id.state_id.name if bills.partner_id.state_id else 'Unknown'

                sheet.write_merge(row, row + col_len, 0, 0, palace_of_supply, style_data)
                sheet.write_merge(row, row + col_len, 1, 1, bills.partner_id.name, style_data)
                sheet.write_merge(row, row + col_len, 2, 2, bills.partner_id.vat if bills.partner_id.vat else " ", style_data)
                sheet.write_merge(row, row + col_len, 3, 3, bills.number, style_data)
                sheet.write_merge(row, row + col_len, 4, 4, bills.date, style_data)
                x = 1
                for bill_item in vendor_bills:
                    sheet.write(row, 5, str(x), style_data)
                    sheet.write(row, 6, bill_item.product_id.name, style_data)
                    sheet.write(row, 7, bill_item.quantity, style_data)
                    sheet.write(row, 8, bill_item.uom_id.name, style_data)
                    sheet.write(row, 9, bill_item.price_unit, style_data)
                    sheet.write(row, 10, bill_item.price_subtotal, style_data)
                    sheet.write(row, 11, bill_item.discount, style_data)
                    sheet.write(row, 12, bill_item.price_subtotal - bill_item.discount, style_data)
                    sheet.write(row, 13, bill_item.tax_id_for_report.amount, style_data)
                    sheet.write(row, 14, bill_item.line_tax_amount, style_data)
                    sheet.write(row, 15, bill_item.line_tax_amount + bill_item.total_excluded_amount, style_data)
                    v_total_qty += bill_item.quantity
                    v_total_amount += bill_item.price_subtotal
                    v_total_discount += bill_item.discount
                    v_total_gross_before_vat += bill_item.price_subtotal - bill_item.discount
                    v_vat_total += bill_item.tax_id_for_report.amount
                    v_total_vat_amount += bill_item.line_tax_amount
                    v_total_amount_with_vat += bill_item.line_tax_amount + bill_item.total_excluded_amount
                    if bill_item.tax_id_for_report.is_standard_rated:
                        purchase_tax_total_vat += bill_item.line_tax_amount
                        purchase_tax_total_ex_amount += bill_item.total_excluded_amount
                    if bill_item.tax_id_for_report.is_reverse_charge:
                        reverse_rated_purchase_total_vat += bill_item.line_tax_amount
                        reverse_rated_purchase_total += bill_item.total_excluded_amount
                    row += 1
                    x += 1
            row += 1
            sheet.write(row, 5, "Total", style0)
            sheet.write(row, 7, v_total_qty, style0)
            sheet.write(row, 10, v_total_amount, style0)
            sheet.write(row, 11, v_total_discount, style0)
            sheet.write(row, 12, v_total_gross_before_vat, style0)
            sheet.write(row, 13, v_vat_total, style0)
            sheet.write(row, 14, v_total_vat_amount, style0)
            sheet.write(row, 15, v_total_amount_with_vat, style0)

        if self.report_type in ['sale', 'all'] and sale_tax_total:
            row += 3

            sheet.write(row, 0, 'VAT on Sales and all other Outputs', style0)
            sheet.write(row, 1, 'Total Amount', style0)
            sheet.write(row, 2, 'Total VAT amount', style0)
            for key in sale_tax_total:
                row += 1
                sheet.write(row, 0, 'Standard Rated Supplies in ' + key, style_data)
                sheet.write(row, 1, sale_tax_total[key][1], style_data)
                sheet.write(row, 2, sale_tax_total[key][0], style_data)
            row += 1
            sheet.write(row, 0, 'Zero Rated Supplies', style_data)
            sheet.write(row, 1, zero_rated_sale_total, style_data)
            sheet.write(row, 2, zero_rated_sale_total_vat, style_data)
            row += 1
            sheet.write(row, 0, 'Exempted Supplies', style_data)
            sheet.write(row, 1, non_tax_total_amount, style_data)
            sheet.write(row, 2, 0.0, style_data)
        if self.report_type in ['purchase', 'all'] and sale_tax_total:
            row += 3
            sheet.write(row, 0, 'VAT on Expenses and all other Inputs', style0)
            sheet.write(row, 1, 'Total Amount', style0)
            sheet.write(row, 2, 'Total VAT amount', style0)
            row += 1
            sheet.write(row, 0, 'Standard rated expenses', style_data)
            sheet.write(row, 1, purchase_tax_total_ex_amount, style_data)
            sheet.write(row, 2, purchase_tax_total_vat, style_data)
            row += 1
            sheet.write(row, 0, 'Supplies subject to the reverse charge provisions', style_data)
            sheet.write(row, 1, reverse_rated_purchase_total, style_data)
            sheet.write(row, 2, reverse_rated_purchase_total_vat, style_data)

        workbook.save('/tmp/vat_report.xls')
        result_file = open('/tmp/vat_report.xls', 'rb').read()
        attachment_id = self.env['wizard.vat_report.info.excel.report'].create({
            'name': 'Tax Report.xls',
            'report': base64.encodestring(result_file)
        })
        return{
            'type': 'ir.actions.act_url',
            'url': '/web/content/wizard.vat_report.info.excel.report/%s/report/vat_report.xls?download=true' %(attachment_id.id),
            'name': 'Report',
        }
        # return {
        #     'name': _('Notification'),
        #     'context': self.env.context,
        #     'view_type': 'form',
        #     'view_mode': 'form',
        #     'res_model': 'wizard.vat_report.info.excel.report',
        #     'res_id': attachment_id.id,
        #     'data': None,
        #     'type': 'ir.actions.act_window',
        #     'target': 'new'
        # }


class PrintWizard(models.TransientModel):
    _name = 'wizard.vat_report.info.excel.report'
    _rec_name = 'name'

    name = fields.Char()
    report = fields.Binary(string="Attach", )


class TaxInAndOutReport(models.AbstractModel):
    _name = 'report.account_tax_report_ft.report_tax_in_out_statement'
    _description = "TaxInAndOutReport"

    def context_date_format(self, value):
        if isinstance(value, basestring):
            value = fields.Datetime.from_string(value)
        lang = self.env['res.lang']._lang_get(self.env.context.get('lang'))
        return datetime.strftime(value, lang.date_format)

    @api.multi
    def render_html(self, docids, data=None):
        tax_ids = []
        tax_id = []
        if not data['tax_filter']:
            for tax in self.env['account.tax'].search([]):
                tax_ids.append(tax)
                tax_id.append(tax.id)
        else:
            tax_items = self.env['account.tax'].browse(data['taxes'])
            for item in tax_items:
                tax_ids.append(item)
                tax_id.append(item.id)

        domain = [('invoice_line_tax_ids', 'in', tax_id)]
        partners = []
        if data['report_type'] != 'purchase' and data['customers']:
            for item in data['customers']:
                partners.append(item)
        if data['report_type'] != 'sale' and data['suppliers']:
            for item in data['suppliers']:
                partners.append(item)
        if partners:
            domain.append(('partner_id', 'in', partners))
        if data.get('from_date'):
            fd = data['from_date']
            domain.append(('invoice_id.date_invoice', '>=', fd))
        if data.get('to_date'):
            td = data['to_date']
            domain.append(('invoice_id.date_invoice', '<=', td))
        journal_items = self.env['account.invoice.line'].search(domain)

        sale_tax_item = []
        purchase_tax_item = []
        for item in journal_items:
            if item.invoice_id.type == 'out_invoice' and data['report_type'] != 'purchase':
                sale_tax_item.append(item)
            if item.invoice_id.type == 'in_invoice' and data['report_type'] != 'sale':
                purchase_tax_item.append(item)

        sale_total = sum(tax.total_excluded_amount for tax in sale_tax_item) if sale_tax_item else 0.0
        # sale_tax_avg = sum(tax.line_tax_amount for tax in sale_tax_item) / (len(sale_tax_item)) if sale_tax_item else 0.0
        sale_tax_total = sum(tax.line_tax_amount for tax in sale_tax_item) if sale_tax_item else 0.0
        sale_total_with_tax = sum(tax.total_included_amount for tax in sale_tax_item) if sale_tax_item else 0.0

        purchase_total = sum(tax.total_excluded_amount for tax in purchase_tax_item) if purchase_tax_item else 0.0
        # purchase_tax_avg = sum(tax.line_tax_amount for tax in purchase_tax_item) / (len(purchase_tax_item)) if purchase_tax_item else 0.0
        purchase_tax_total = sum(tax.line_tax_amount for tax in purchase_tax_item) if purchase_tax_item else 0.0
        purchase_total_with_tax = sum(
            tax.total_included_amount for tax in purchase_tax_item) if purchase_tax_item else 0.0

        # sale_tax_item.sort(key=lambda k: (k['inv_date'], k.invoice_id.name))
        # purchase_tax_item.sort(key=lambda k: (k['inv_date'], k.invoice_id.name))
        if not sale_tax_item and not purchase_tax_item:
            raise UserError(_('There is no VAT Entries For The Selected Items'))

        docargs = {
            'docs': journal_items,
            'sale_tax_item': sale_tax_item,
            'purchase_tax_item': purchase_tax_item,
            'from_date': self.context_date_format(fd),
            'to_date': self.context_date_format(td),
            'tax_ids': tax_ids,
            'sale_total': sale_total,
            # 'sale_tax_avg': sale_tax_avg,
            'sale_tax_total': sale_tax_total,
            'sale_total_with_tax': sale_total_with_tax,
            'purchase_total': purchase_total,
            # 'purchase_tax_avg': purchase_tax_avg,
            'purchase_tax_total': purchase_tax_total,
            'purchase_total_with_tax': purchase_total_with_tax,
        }
        return self.env['report'].render('account_tax_report_ft.report_tax_in_out_statement', docargs)
