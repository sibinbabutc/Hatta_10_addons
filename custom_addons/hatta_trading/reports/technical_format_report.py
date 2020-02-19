from odoo.addons.report_xlsx.report.report_xlsx import ReportXlsx


class TechnicalXlsx(ReportXlsx):

    def generate_xlsx_report(self, workbook, data, invoices):
        for obj in invoices:
            sheet = workbook.add_worksheet('Technical Offer')

            content_format = workbook.add_format({
                'border': 1,
                'font_size': 11,
                'valign': 'vcenter',
            })
            content_format_left1 = workbook.add_format({
                'font_size': 11,
                'valign': 'vcenter',
                'align': 'left',
                'bold':1,
                'left':2,
                'right':1,
                'bottom':1,
                'top':1,
            })
            content_format_right1 = workbook.add_format({

                'font_size': 11,
                'valign': 'vcenter',
                'align': 'left',
                'left':1,
                'right':2,
                'bottom':1,
                'top':1,
            })
            content_format_right1a = workbook.add_format({

                'font_size': 11,
                'valign': 'vcenter',
                'align': 'left',
                'left':1,
                'right':2,
                'bottom':1,
                'top':1,
                'bold':1,
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
            content_format_top1a = workbook.add_format({
                'font_size': 11,
                'valign': 'vcenter',
                'align': 'left',
                'left': 2,
                'right': 2,
                'bottom': 1,
                'top': 2,
            })
            content_format_top1b = workbook.add_format({
                'font_size': 11,
                'align': 'left',
                'left': 2,
                'right': 2,
                'bottom': 2,
                'top': 1,
            })

            format_l_f_col = workbook.add_format({"left": 2,"right": 2,'top':1,'bottom':1})
            format_bottom_col = workbook.add_format({"bottom": 2,"left":2,"right": 2})

            sheet.merge_range('C6:E6','REQUEST FOR QUOTATION',content_format_bold,)

            sheet.write('C7','RFQ TITLE',content_format_bold)
            # if obj.enquiry_id.reference:
            #     width = len(obj.enquiry_id.reference)
            sheet.merge_range('D7:E7',obj.enquiry_id.reference,content_format_bold)

            sheet.write('C8','RFQ NO:',content_format_bold)
            sheet.merge_range('D8:E8',obj.name,content_format_bold)

            sheet.merge_range('C10:K10','TECHNICAL OFFER',content_format_top1)

            sheet.write('C11','SECTION 1',content_format_left1)
            sheet.write('D11','QUALIFICATION STATEMENT',content_format_bold)
            sheet.merge_range('E11:K11','APPENDIX ATTACHED',content_format_right1a)

            row = 12
            new_row = row + 1

            sheet.set_column(2, 2, 10)
            sheet.write('C%s'%(row),'SECTION 2',content_format_left1)
            sheet.set_column(3, 3, 25)
            sheet.write('D%s'%(row),'TECHNICAL BID',content_format_center)
            sheet.set_column(4, 4, 10)
            sheet.write('E%s'%(row),'RFQ ITEM',content_format_center)
            sheet.set_column(5, 5, 20)
            sheet.write('F%s'%(row),'MATERIAL NUMBER',content_format_center)
            sheet.set_column(6, 6, 35)
            sheet.write('G%s'%(row),'SHORT TEXT',content_format_center)
            sheet.write('H%s'%(row),'QTY',content_format_center)
            sheet.write('I%s'%(row),'UOM',content_format_center)
            sheet.set_column(9, 9, 10)
            sheet.write('J%s'%(row),'UNIT PRICE',content_format_center)
            sheet.set_column(10, 10, 18)
            sheet.write('K%s'%(row),'LINE ITEM TOTAL',content_format_right1a)

            for x in obj.order_line:
                sheet.write('C%s' % new_row, '',content_format_left1)
                sheet.write('D%s' % new_row, '',content_format)
                sheet.write('E%s' % new_row,x.serial_no,content_format_centernb)
                sheet.write('F%s' % new_row,x.product_id.default_code,content_format)
                sheet.write('G%s' % new_row,x.name,content_format)
                sheet.write('H%s' % new_row,x.product_qty,content_format_centernb)
                sheet.write('I%s' % new_row,x.product_uom.name,content_format_centernb)
                sheet.write('J%s' % new_row,'QUOTED',content_format)
                sheet.write('K%s' % new_row,'QUOTED',content_format_right1)
                new_row += 1

            sheet.merge_range('E%s:K%s'% ((new_row ),(new_row)),obj.company_id.currency_id.name,content_format_right1)

            sheet.merge_range('E%s:K%s'%((new_row + 1),(new_row + 1)),'1. DETAILED SPECIFICATION:',content_format_top1a)

            sheet.merge_range('E%s:K%s'%((new_row + 2),(new_row + 2)),'2. COPY OF OUR MINISTRY OF ECONOMY CERTIFICATE AND AGENCY AGREEMENT CERTIFICATE -N/A',format_l_f_col)

            sheet.merge_range('E%s:K%s'%((new_row + 3),(new_row + 3)),'3. MFR NAME:',format_l_f_col)

            sheet.merge_range('E%s:K%s'%((new_row + 4),(new_row + 4)),'4. CERTIFICATE OF ORIGIN:',format_l_f_col)

            sheet.merge_range('E%s:K%s'%((new_row + 5),(new_row + 5)),'5. DELIVERY: AS MENTIONED IN APPENDIX',content_format_top1b)

            sheet.write('C%s'%(new_row + 8),'SECTION 4',content_format_bold)
            sheet.write('D%s'%(new_row + 8),'CERTIFICATION',content_format_bold)

            sheet.merge_range('E%s:K%s'%((new_row + 8),(new_row + 8)),'AS MENTIONED IN APPENDIX',content_format_right1)

            sheet.write('C%s'%(new_row + 9),'SECTION 5',content_format_bold)
            sheet.write('D%s'%(new_row + 9),'QUOTED DELIVERY IN WEEKS',content_format_bold)
            sheet.merge_range('E%s:K%s'%((new_row + 9),(new_row + 9)),'AS MENTIONED IN APPENDIX',content_format_right1)
            sheet.merge_range('C%s:K%s'%((new_row + 10),(new_row + 10)),'',format_bottom_col)

            sheet.merge_range('D%s:K%s' % ((new_row + 6), (new_row + 6)),'', content_format_right1)
            sheet.merge_range('D%s:K%s' % ((new_row + 7), (new_row + 7)),'',content_format_right1)

            # conditional

            sheet.conditional_format('C%s:C%s' % ((new_row ), (new_row + 9)), {'type': 'blanks', 'format': content_format_left1})
            sheet.conditional_format('C%s:C%s' % ((new_row ), (new_row + 9)), {'type': 'no_blanks', 'format': content_format_left1})

            sheet.conditional_format('D%s:D%s' % ((new_row + 1), (new_row + 5)), {'type': 'blanks', 'format': content_format_right1})
            sheet.conditional_format('D%s:D%s' % ((new_row + 1), (new_row + 5)), {'type': 'no_blanks', 'format': content_format_right1})
            sheet.conditional_format('D%s'% new_row, {'type': 'blanks', 'format': content_format})
            sheet.conditional_format('D%s'% new_row, {'type': 'no_blanks', 'format': content_format})




TechnicalXlsx('report.technical.format.xlsx','purchase.order')

