from openerp.addons.report_xlsx.report.report_xlsx import ReportXlsx
from odoo import api, fields, models, _
from odoo.tools import english_number



def amount_to_text_ae(number):
    number = '%.2f' % number
    units_name = 'Dirhams'
    list = str(number).split('.')
    start_word = english_number(int(list[0]))
    end_word = english_number(int(list[1]))
    fils_name = 'Fils'

    return ' '.join(filter(None,
                           [start_word, units_name, (start_word or units_name) and (end_word or fils_name) and 'and',
                            end_word, fils_name]))


class PartnerXlsx(ReportXlsx):


    def generate_xlsx_report(self, workbook, data, invoices):
        for obj in invoices:
            amount_in_words2 = fields.Char('Amount in Words', compute='get_amount_in_words2', store=True)
            sheet = workbook.add_worksheet('Commercial Bid')

            content_format = workbook.add_format({
                'border': 1,
                'font_size': 11,
                'valign': 'vcenter',
            })

            content_format_top1 = workbook.add_format({
                'font_size': 11,
                'valign': 'vcenter',
                'align': 'center',
                'bold': 1,
                'left': 2,
                'right': 2,
                'bottom': 1,
                'top': 2,
            })
            content_format_right = workbook.add_format({
                'border': 1,
                'font_size': 11,
                'valign': 'vcenter',
                'align': 'right',
            })
            content_format_right1a = workbook.add_format({

                'font_size': 11,
                'valign': 'vcenter',
                'align': 'center',
                'left': 2,
                'right': 1,
                'bottom': 1,
                'top': 1,
                'bold': 1,
            })
            content_format_right1b = workbook.add_format({

                'font_size': 11,
                'valign': 'vcenter',
                'align': 'right',
                'left': 1,
                'right': 2,
                'bottom': 1,
                'top': 1,
            })
            content_format_right1c = workbook.add_format({

                'font_size': 11,
                'valign': 'vcenter',
                'align': 'center',
                'left': 1,
                'right': 2,
                'bottom': 1,
                'top': 1,
                'bold':1
            })
            content_format_right1d = workbook.add_format({

                'font_size': 11,
                'valign': 'vcenter',
                'align': 'left',
                'left': 1,
                'right': 2,
                'bottom': 1,
                'top': 1,
            })
            content_format_bold = workbook.add_format({
                'border': 1,
                'font_size': 11,
                'valign': 'vcenter',
                'bold': 1})
            content_format_center = workbook.add_format({
                'border': 1,
                'font_size': 11,
                'align': 'center',
                'valign': 'vcenter',
                'bold': 1})
            content_format_centernb = workbook.add_format({
                'border': 1,
                'font_size': 11,
                'align': 'center',
                'valign': 'vcenter',
            })

            format_bottom_col = workbook.add_format({"bottom": 2, "left": 2, "right": 2})

            sheet.merge_range('C6:E6','REQUEST FOR QUOTATION', content_format_bold)
            sheet.write('C7','RFQ TITLE', content_format_bold)
            # if obj.enquiry_id.reference:
            #     width = len(obj.enquiry_id.reference)
            sheet.merge_range('D7:E7',obj.enquiry_id.reference, content_format_bold)

            sheet.write('C8', 'RFQ NO:', content_format_bold)
            sheet.merge_range('D8:E8', obj.name, content_format_bold)

            sheet.merge_range('C10:K10', 'COMMERCIAL OFFER', content_format_top1)

            sheet.write('C11','SECTION 1', content_format_right1a)
            sheet.merge_range('D11:K11','COMMERCIAL BID SUBMISSION FORM', content_format_right1c)

            row = 12
            new_row = row + 1

            sheet.set_column(2, 2, 10)
            sheet.write('C%s'%(row),'', content_format_right1a)
            sheet.set_column(3, 3, 30)
            sheet.write('D%s'%(row),'', content_format_center)
            sheet.set_column(4,4,10)
            sheet.write('E%s'%(row),'RFQ ITEM', content_format_center)
            sheet.set_column(5,5,20)
            sheet.write('F%s'%(row),'MATERIAL NUMBER ', content_format_center)
            sheet.set_column(6,6,35)
            sheet.write('G%s'%(row),'SHORT TEXT', content_format_center)
            sheet.write('H%s'%(row),'QTY', content_format_center)
            sheet.write('I%s'%(row),'UOM', content_format_center)
            sheet.set_column(9,9,10)
            sheet.write('J%s'%(row),'UNIT PRICE', content_format_center)
            sheet.set_column(10,10, 18)
            sheet.write('K%s'%(row),'LINE ITEM TOTAL', content_format_right1c)

            total_price = 0
            for x in obj.order_line:

                sheet.write('E%s'%(new_row),x.serial_no,content_format_centernb)
                sheet.write('F%s'%(new_row),x.product_id.default_code,content_format)
                sheet.write('G%s'%(new_row),x.name,content_format)
                sheet.write('H%s'%(new_row),x.product_qty,content_format_centernb)
                sheet.write('I%s'%(new_row),x.product_uom.name,content_format_centernb)
                sheet.write('J%s'%(new_row),'%.2f' % x.price_unit_lc,content_format_right)
                sheet.write('K%s'%(new_row),'%.2f' % x.price_total_lc,content_format_right1b)
                new_row += 1
                total_price = total_price + x.price_total_lc

            sheet.merge_range('C%s:C%s' % ((row + 1), (new_row )), 'SECTION 2', content_format_right1a)
            sheet.merge_range('D%s:D%s' % ((row + 1), (new_row)), 'SCHEDULE OF FEES', content_format_center)

            amount_in_words2 = amount_to_text_ae(total_price)

            sheet.write('J%s'%(new_row),'TOTAL',content_format)
            sheet.write('K%s'%(new_row),'%.2f' %total_price,content_format_right1b)

            sheet.merge_range('E%s:K%s'%((new_row + 1),(new_row + 1)),amount_in_words2,content_format_right1d)

            sheet.write('C%s'%(new_row + 1),'',content_format_right1a)

            sheet.write('C%s'%(new_row + 2),'SECTION 3',content_format_right1a)
            sheet.write('D%s'%(new_row + 2),'POWER OF ATTORNEY',content_format)
            sheet.merge_range('E%s:K%s' % ((new_row + 2),(new_row + 2)),'ATTACHED',content_format_right1d)

            sheet.write('C%s'%(new_row + 3),'SECTION 4',content_format_right1a)
            sheet.write('D%s'%(new_row + 3),'CURRENCY',content_format)
            sheet.merge_range('E%s:K%s'% ((new_row + 3),(new_row + 3)),obj.company_id.currency_id.name,content_format_right1d)

            sheet.write('C%s'%(new_row + 4),'SECTION 5',content_format_right1a)
            sheet.write('D%s'%(new_row + 4),'CURRENCY',content_format)
            sheet.merge_range('E%s:K%s'% ((new_row + 4),(new_row + 4)),'N/A',content_format_right1d)

            sheet.write('C%s'%(new_row + 5),'SECTION 6',content_format_right1a)
            sheet.write('D%s'%(new_row + 5),'QUOTED DELIVERY IN WEEK',content_format)
            sheet.merge_range('E%s:K%s'% ((new_row + 5),(new_row + 5)),'AS MENTIONED IN APPENDIX',content_format_right1d)

            sheet.merge_range('C%s:K%s'%((new_row + 6),(new_row + 6)),'',format_bottom_col)



PartnerXlsx('report.commercial.format.xlsx','purchase.order')

