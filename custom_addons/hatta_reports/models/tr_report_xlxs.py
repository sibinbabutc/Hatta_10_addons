from odoo.addons.report_xlsx.report.report_xlsx import ReportXlsx
from datetime import datetime


class Tr_reportXlsx(ReportXlsx):

    def generate_xlsx_report(self, workbook, data, invoices):
        tr_reciept_obj = self.env['tr.details']
        tr_account_obj = self.env['tr.account']
        open_tr = tr_reciept_obj.get_open_tr_amount()
        settled_tr = tr_reciept_obj.get_settle_tr_amount()
        total_tr = tr_reciept_obj.get_total_tr_amount()
        tr_limit = tr_account_obj.get_tr_limit()
        tr_balance = tr_account_obj.get_tr_balance()
        printed_date = datetime.today().strftime('%d-%m-%Y')

        domain = []
        if self.env.context.get('tr'):
            domain.append(('tr_account_id', '=', self.env.context.get('tr')))

        # if data['partner_id']:
        #     domain.append(('partner_id','=',data['partner_id']))
        if self.env.context.get('date_from'):
            date1 = datetime.strptime(self.env.context.get('date_from'), '%Y-%m-%d')
            d1 = datetime.strftime(date1, "%Y-%m-%d 00:00:00")
            domain.append(('closing_date', '>=', d1))
        if self.env.context.get('date_to'):
            date2 = datetime.strptime(self.env.context.get('date_to'), '%Y-%m-%d')
            d2 = datetime.strftime(date2, "%Y-%m-%d 23:59:59")
            domain.append(('closing_date', '<=', d2))
        if self.env.context.get('state'):
            domain.append(('state', '=', self.env.context.get('state')))
        if not self.env.context.get('state'):
            domain.append(('state', '!=', 'draft'))

        docs = self.env['tr.details'].search(domain)

        format2 = workbook.add_format({
            'num_format': 'dd/mm/yy',
            'border': 1,
            'font_size': 10,
            'valign': 'vcenter',
            'align': 'center'
        })
        content_format_bold = workbook.add_format({
            'border': 1,
            'font_size': 10,
            'valign': 'vcenter',
            'bold': 1,
            'align': 'center'
        })
        content_format_center = workbook.add_format({
            'border': 1,
            'font_size': 10,
            'valign': 'vcenter',
            'align': 'center'
        })
        content_format_left = workbook.add_format({
            'border': 1,
            'font_size': 10,
            'valign': 'vcenter',
            'align': 'left'
        })
        content_format_right = workbook.add_format({
            'border': 1,
            'font_size': 10,
            'valign': 'vcenter',
            'align': 'right'
        })
        content_format = workbook.add_format({
            'border': 1,
            'font_size': 10,
            'valign': 'vcenter',
        })
        border_left_top = workbook.add_format({
            'font_size': 10,
            'valign': 'vcenter',
            'align': 'left',
            'left': 1,
            'right': 0,
            'bottom': 0,
            'top': 1,
            'bold': 1,
        })
        border_left_bottom = workbook.add_format({
            'font_size': 10,
            'valign': 'vcenter',
            'align': 'left',
            'left': 1,
            'right': 0,
            'bottom': 1,
            'top': 0,
            'bold': 1,
        })
        border_right_top = workbook.add_format({
            'font_size': 10,
            'valign': 'vcenter',
            'align': 'left',
            'left': 0,
            'right': 1,
            'bottom': 0,
            'top': 1,
        })
        border_right_bottom = workbook.add_format({
            'font_size': 10,
            'valign': 'vcenter',
            'align': 'left',
            'left': 0,
            'right': 1,
            'bottom': 1,
            'top': 0,
            'bold': 1,
        })
        border_right = workbook.add_format({
            'font_size': 10,
            'valign': 'vcenter',
            'align': 'left',
            'left': 0,
            'right': 1,
            'bottom': 0,
            'top': 0,
        })
        border_left = workbook.add_format({
            'font_size': 10,
            'valign': 'vcenter',
            'align': 'left',
            'left': 1,
            'right': 0,
            'bottom': 0,
            'top': 0,
            'bold': 1,

        })

        sheet = workbook.add_worksheet('TR Report')

        sheet.write('A1', 'Printed On')
        sheet.write('B1',printed_date)

        sheet.merge_range('A3:J3', 'TR REPORT', content_format_bold)
        sheet.merge_range('A4:J4', '(TR:%s)'%(self.env.context.get('tr_acc_name') or ''), )
        # sheet.merge_range('A4:J4', '(TR:)',)

        sheet.set_column(0, 0, 14)
        sheet.write('A5', 'Sl#', content_format_bold)
        sheet.set_column(1, 1, 14)
        sheet.write('B5', 'TR#', content_format_bold)

        sheet.set_row(4, 25)
        sheet.set_column(2, 2, 12)
        sheet.write('C5', 'START DATE', content_format_bold)
        sheet.set_column(3, 3, 14)
        sheet.write('D5', 'CLOSING DATE', content_format_bold)
        sheet.set_column(4, 4, 8)
        sheet.write('E5', 'AMOUNT', content_format_bold)
        sheet.set_column(5, 5, 16)
        sheet.write('F5', 'INTEREST RATE', content_format_bold)
        sheet.set_column(6, 6, 16)
        sheet.write('G5', 'DURATION DAYS', content_format_bold)
        sheet.set_column(7, 7, 20)
        sheet.write('H5', 'INTEREST AS ON TODAY', content_format_bold)
        sheet.set_column(8, 8, 20)
        sheet.write('I5', 'INTEREST AS ON CLOSING', content_format_bold)
        sheet.set_column(9, 9, 30)
        sheet.write('J5', 'PURPOSE', content_format_bold)

        new_row = 5
        sl_no = 0
        sum_amt = 0.0
        interest_tdy = 0.0
        interest_clos = 0.0

        for obj in docs:
            new_row += 1
            sl_no += 1

            sheet.write('A%s' % new_row, sl_no, content_format_center)
            sheet.write('B%s' % new_row, obj.name, content_format_center)
            sheet.write('C%s' % new_row, datetime.strptime(obj.start_date, '%Y-%m-%d'), format2)
            sheet.write('D%s' % new_row, datetime.strptime(obj.closing_date, '%Y-%m-%d'), format2)
            sheet.write('E%s' % new_row, obj.amount, content_format)
            sheet.write('F%s' % new_row, obj.interest_rate, content_format)
            sheet.write('G%s' % new_row, obj.duration, content_format)
            sheet.write('H%s' % new_row, '{0:,.2f}'.format(float(obj.interest_today)), content_format_right)
            sheet.write('I%s' % new_row, '{0:,.2f}'.format(float(obj.final_interest)), content_format_right)
            sheet.write('J%s' % new_row, obj.note, content_format_left)

            sum_amt = sum_amt + obj.amount
            interest_tdy = interest_tdy + obj.interest_today
            interest_clos = interest_clos + obj.final_interest

        sheet.merge_range('A%s:D%s' % ((new_row + 1), (new_row + 1)), '', content_format)
        sheet.write('E%s' % (new_row + 1), sum_amt, content_format_right)
        sheet.merge_range('F%s:G%s' % ((new_row + 1), (new_row + 1)), '', content_format)
        sheet.write('H%s' % (new_row + 1), '{0:,.2f}'.format(float(interest_tdy)), content_format_right)
        sheet.write('I%s' % (new_row + 1), '{0:,.2f}'.format(float(interest_clos)), content_format_right)
        sheet.write('J%s' % (new_row + 1), '', content_format)

        sheet.write('A%s' % (new_row + 3), 'TOTAL TR:',border_left_top)
        sheet.write('B%s' % (new_row + 3), total_tr,border_right_top)

        sheet.write('A%s' % (new_row + 4), 'OPEN TR:',border_left)
        sheet.write('B%s' % (new_row + 4), open_tr,border_right)

        sheet.write('A%s' % (new_row + 5), 'CLOSED TR:',border_left)
        sheet.write('B%s' % (new_row + 5), settled_tr,border_right)

        sheet.write('A%s' % (new_row + 6), 'COMPANY TR LIMIT:',border_left)
        sheet.write('B%s' % (new_row + 6), tr_limit,border_right)

        sheet.write('A%s' % (new_row + 7), 'BALANCE TR:',border_left_bottom)
        sheet.write('B%s' % (new_row + 7), tr_balance,border_right_bottom)


Tr_reportXlsx('report.xls_format_tr_report.xlsx', 'tr.report')
