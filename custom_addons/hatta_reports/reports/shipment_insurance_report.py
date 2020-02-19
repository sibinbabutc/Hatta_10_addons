from odoo.addons.report_xlsx.report.report_xlsx import ReportXlsx
from datetime import datetime

class ShipIns(ReportXlsx):

    def generate_xlsx_report(self, workbook, data, invoices):

        product_obj = self.env['purchase.order'].search([('location_id.usage', '=', 'internal')])
        worksheet = workbook.add_worksheet('Shipment Insurance Report')

        header_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'bold': 1,
            'valign': 'vcenter',
            'font_size': 11
            })
        content_format_center = workbook.add_format({
            'border': 1,
            'align': 'center',
            'font_size': 9,
            'valign': 'vcenter',
            })

        content_format = workbook.add_format({
            'border': 1,
            'font_size': 9,
            'valign': 'vcenter',
            })

        content_format_bold = workbook.add_format({
            'border': 1,
            'font_size': 9,
            'valign': 'vcenter',
            'bold': 1
            })

        worksheet.merge_range('A1:Q4', self.env.user.company_id.name, header_format)
        #worksheet.merge_range('A3:Q3', 'Stock Report As On %s' % datetime.strftime(datetime.today(), '%d-%m-%Y'), content_format_center)

        row = 5
        col = 0
        new_row = row + 1
        worksheet.write('A%s' %(row), 'SlNo', content_format)
        worksheet.write('B%s' %(row), 'Date', content_format)
        worksheet.write('C%s' %(row), 'Order No', content_format)
        worksheet.write('D%s' %(row), 'Bank & LC No', content_format)
        worksheet.write('E%s' %(row), 'Bill Of Lading No', content_format)
        worksheet.write('F%s' %(row), 'Product', content_format)
        worksheet.write('G%s' %(row), 'By Sea/Air/Road/Rail %', content_format)
        worksheet.write('H%s' %(row), 'Vessel No %', content_format)
        worksheet.write('I%s' %(row), 'Voyage %', content_format)
        worksheet.write('J%s' %(row), 'Curr', content_format)
        worksheet.write('K%s' %(row), 'Invoice Value', content_format)
        worksheet.write('L%s' %(row), 'C&F +10%', content_format)
        worksheet.write('M%s' %(row), 'Enchange Rate', content_format)
        worksheet.write('N%s' %(row), 'Premium Amount(AED)',content_format)
        worksheet.write('O%s' %(row), 'Supplier Name', content_format)
        worksheet.write('P%s' %(row), 'PO A/C No', content_format)

        # partner_state = self.env.user.company_id.partner_id.state_id.name
        # i = 1
        # total_amount = 0.0
        # for obj in product_obj:
        #     cgst = 0.0
        #     sgst = 0.0
        #     igst = 0.0
        #     total_amount += obj.inventory_value
        #     for x in obj.product_id.taxes_id:
        #         if x.tax_type == 'cgst':
        #             cgst += x.amount
        #         if x.tax_type == 'sgst':
        #             sgst += x.amount
        #         if x.tax_type == 'igst':
        #             igst += x.amount
        #     worksheet.write('A%s' %(new_row), i, content_format)
        #     worksheet.write('B%s' %(new_row), obj.product_id.name, content_format)
        #     worksheet.write('C%s' %(new_row), obj.qty, content_format)
        #     worksheet.write('D%s' %(new_row), obj.product_id.uom_id.name, content_format)
        #     worksheet.write('E%s' %(new_row), obj.cost, content_format)
        #     worksheet.write('F%s' %(new_row), obj.product_id.list_price, content_format)
        #     worksheet.write('G%s' %(new_row), cgst, content_format)
        #     worksheet.write('H%s' %(new_row), sgst, content_format)
        #     worksheet.write('I%s' %(new_row), igst, content_format)
        #     worksheet.write('J%s' %(new_row), obj.product_id.hsn_code, content_format)
        #     worksheet.write('K%s' %(new_row), obj.inventory_value, content_format)
        #     new_row += 1
        #     i += 1
        # worksheet.write('B%s' % (new_row+1), 'Total', content_format_bold)
        # worksheet.write('K%s' % (new_row+1), total_amount, content_format_bold)


ShipIns('report.hatta_reports.insurance.xlsx', 'purchase.order')