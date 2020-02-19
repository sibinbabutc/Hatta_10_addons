import logging
from datetime import datetime
from cStringIO import StringIO
from odoo.report.report_sxw import report_sxw
from odoo.api import Environment

_logger = logging.getLogger(__name__)

try:
    import xlsxwriter
except ImportError:
    _logger.debug('Can not import xlsxwriter`.')


class ReportXlsx(report_sxw):

    def create(self, cr, uid, ids, data, context=None):
        self.env = Environment(cr, uid, context)
        report_obj = self.env['ir.actions.report.xml']
        report = report_obj.search([('report_name', '=', self.name[7:])])
        if report.ids:
            self.title = report.name
            if report.report_type == 'xlsx':
                return self.create_xlsx_report(ids, data, report)
        return super(ReportXlsx, self).create(cr, uid, ids, data, context)

    def create_xlsx_report(self, ids, data, report):
        self.parser_instance = self.parser(
            self.env.cr, self.env.uid, self.name2, self.env.context)
        objs = self.getObjects(
            self.env.cr, self.env.uid, ids, self.env.context)
        self.parser_instance.set_context(objs, data, ids, 'xlsx')
        file_data = StringIO()
        workbook = xlsxwriter.Workbook(file_data)
        self.generate_xlsx_report(workbook, data, objs)
        workbook.close()
        file_data.seek(0)
        return (file_data.read(), 'xlsx')

    def generate_xlsx_report(self, workbook, data, objs):
        raise NotImplementedError()

class PayrollBatchXlsx(ReportXlsx):

    def generate_xlsx_report(self, workbook, data, obj):

        report_obj = self.env['hr.payslip.run'].browse(obj.id)
        worksheet = workbook.add_worksheet('Payslip Batch Report')
        date_format = workbook.add_format({
            'num_format': 'dd-mm-yyyy',
            'border': 1,
            'font_size': 9,
            'valign': 'vcenter',
        })

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

        start_date = datetime.strftime(datetime.strptime(self.env.context.get('start_date'), '%Y-%m-%d'), '%d-%m-%Y')
        end_date = datetime.strftime(datetime.strptime(self.env.context.get('end_date'), '%Y-%m-%d'), '%d-%m-%Y')
        worksheet.merge_range('A1:P1', self.env.user.company_id.name, header_format)
        worksheet.merge_range('A2:P2', 'Item Wise Purchase Report From %s to %s'
                              % (start_date, end_date), content_format_center)
        worksheet.set_column(3, 2, 15)
        row = 3
        col = 0
        new_row = row + 1
        worksheet.write('A%s' %(row), 'Sl No', content_format)
        worksheet.write('B%s' %(row), 'Name', content_format)
        worksheet.write('C%s' %(row), 'Emp Sl Code', content_format)
        worksheet.write('D%s' %(row), 'Employee IBAN Number', content_format)
        worksheet.write('E%s' %(row), 'Mode of Transfer', content_format)
        worksheet.write('F%s' %(row), 'Labour ID Number', content_format)
        worksheet.write('G%s' %(row), 'Basic', content_format)
        worksheet.write('H%s' %(row), 'HRA', content_format)
        worksheet.write('I%s' %(row), 'Travel Allowance', content_format)
        worksheet.write('J%s' %(row), 'Other Allowance', content_format)
        worksheet.write('K%s' %(row), 'Food Allowance', content_format)
        worksheet.write('L%s' %(row), 'Petrol Allow', content_format)
        worksheet.write('M%s' %(row), 'Total Income', content_format)
        worksheet.write('O%s' %(row), 'Days Worked', content_format)
        worksheet.write('P%s' %(row), 'Special Incentive', content_format)
        worksheet.write('Q%s' %(row), 'Leave Salary', content_format)
        worksheet.write('R%s' %(row), 'Salary Earned', content_format)
        worksheet.write('S%s' %(row), 'Salary Advance', content_format)
        worksheet.write('T%s' %(row), 'Family Allowance', content_format)
        worksheet.write('U%s' %(row), 'Overtime Allow', content_format)
        worksheet.write('V%s' %(row), 'Total Salary', content_format)
        worksheet.write('W%s' %(row), 'Pending Advances', content_format)
        worksheet.write('X%s' %(row), 'Advance Deduction', content_format)
        worksheet.write('Y%s' %(row), 'Tel Charge Ded', content_format)
        worksheet.write('Z%s' %(row), 'Total Deduction', content_format)
        worksheet.write('AA%s' %(row), 'Net Salary Paid', content_format)

        i = 1
        for item in report_obj.slip_ids:
            # basic = 0.0
            # hra = 0.0
            # ta = 0.0
            # oa = 0.0
            # fa = 0.0
            # palw = 0.0
            #
            # for rec in item.line_ids:

            worksheet.write('A%s' %(new_row), i, content_format)
            worksheet.write('B%s' %(new_row), item.employee_id.name, content_format)
            worksheet.write('C%s' %(new_row), item.employee_id.employee_number, content_format)
            worksheet.write('D%s' %(new_row), item.employee_id.bank_account_id.acc_number, content_format)
            worksheet.write('E%s' %(new_row), item.employee_id.sal_transfer_mode, content_format)
            worksheet.write('F%s' %(new_row), item.employee_id.labour_card_no, content_format)
            # worksheet.write('G%s' %(new_row), obj.uom_id.name, content_format)
            # worksheet.write('H%s' %(new_row), obj.price_unit, content_format)
            # worksheet.write('I%s' %(new_row), customer.name, content_format)
            # worksheet.write('J%s' %(new_row), cgst, content_format)
            # worksheet.write('K%s' %(new_row), cgst_amount, content_format)
            # worksheet.write('L%s' %(new_row), sgst, content_format)
            # worksheet.write('M%s' %(new_row), sgst_amount, content_format)
            # worksheet.write('N%s' %(new_row), igst, content_format)
            # worksheet.write('O%s' %(new_row), igst_amount, content_format)
            # worksheet.write('P%s' %(new_row), amount, content_format)
            new_row += 1
            i += 1

PayrollBatchXlsx('report.hr.payroll.batch.xlsx', 'hr.payslip.run')
