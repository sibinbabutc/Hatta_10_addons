from odoo import fields, models, api
import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT


def get_years():
    year_list = []
    for i in range(2016, 2036):
        year_list.append((i, str(i)))
    return year_list


def last_day_of_month(any_day):
    next_month = any_day.replace(day=28) + datetime.timedelta(days=4)  # this will never fail
    return next_month - datetime.timedelta(days=next_month.day)


class GymReportWizard(models.TransientModel):
    _name = "petty_cash.report.wizard"

    def _get_readonly(self):
        return self.user.user_has_groups('account.group_pettycash_custodian')

    pettycash_user = fields.Many2one("pettycash.fund", string="Petty Cash Fund (Custodian)")
    from_date = fields.Date('Start Date')
    to_date = fields.Date('End Date')
    view_type = fields.Selection([('day', 'By Date'), ('month', 'By Month'), ('year', 'By Year')])
    months = fields.Selection([('01', 'January'), ('02', 'February'), ('03', 'March'), ('04', 'April'),
                               ('05', 'May'), ('06', 'June'), ('07', 'July'), ('08', 'August'),
                               ('09', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')],
                              "Month")
    year = fields.Selection(get_years(), string='Year', )

    @api.multi
    def print_report(self):
        return self.env['report'].get_action(self, 'account_petty_cash_ft.report_print_petty_cash_statement',
                                             data={'from_date': self.from_date,
                                                   'to_date': self.to_date,
                                                   'view_type': self.view_type,
                                                   'month': self.months,
                                                   'year': self.year,
                                                   'pettycash_user': self.pettycash_user.id,
                                                   'account_id': self.pettycash_user.custodian_account.id
                                                   })


class GymReport(models.AbstractModel):
    _name = 'report.account_petty_cash_ft.report_print_petty_cash_statement'

    @api.multi
    def render_html(self, docids, data=None):
        move_domain = [('account_id', '=', data['account_id']),
                       ('pettycash_id', '=', data['pettycash_user'])]
        balance_domain = [('account_id', '=', data['account_id']),
                          ('pettycash_id', '=', data['pettycash_user'])]

        open_balance_date = data['from_date']
        from_to = []
        if data['view_type'] == 'day' and data['from_date']:
            open_balance_date = datetime.datetime.strptime(data['from_date'], "%Y-%m-%d")
            balance_domain.append(('date', '<', data['from_date']))
            if not data['to_date']:
                move_domain.append(('date', 'like', data['from_date']))
            if data['to_date']:
                to_print_from_date = datetime.datetime.strptime(data['from_date'], "%Y-%m-%d")
                to_print_to_date_date = datetime.datetime.strptime(data['to_date'], "%Y-%m-%d")
                from_to.append(['Period'])
                from_to.append([to_print_from_date.strftime("%d-%m-%Y")])
                from_to.append(['To %s' % to_print_to_date_date.strftime("%d-%m-%Y")])
                date_1 = datetime.datetime.strptime(data['to_date'], "%Y-%m-%d")
                end_date = date_1 + datetime.timedelta(days=+1)
                move_domain.append(('date', '>=', data['from_date']))
                move_domain.append(('date', '<', end_date))
            else:
                to_print_from_date = datetime.datetime.strptime(data['from_date'], "%Y-%m-%d")
                from_to.append(['Date : %s' % to_print_from_date.strftime("%d-%m-%Y")])
        elif data['view_type'] == 'month' and data['month']:
            month = [['01', 'January'], ['02', 'February'], ['03', 'March'], ['04', 'April'],
                     ['05', 'May'], ['06', 'June'], ['07', 'July'], ['08', 'August'],
                     ['09', 'September'], ['10', 'October'], ['11', 'November'], ['12', 'December']]
            if data['year']:
                month_year = ('%s-%s-' % (data['year'], data['month']))
                month_year_balance = datetime.datetime.strptime(('%s-%s-01' % (data['year'], data['month'])), "%Y-%m-%d")
                open_balance_date = datetime.datetime.date(month_year_balance)
                move_domain.append(('date', 'like', month_year))
                balance_domain.append(('date', '<', month_year_balance))
            for item in month:
                if data['month'] == item[0]:
                    from_to.append(['Month - %s, %s' % (item[1], data['year'])])

        elif data['year']:
            year = ('%s-' % (data['year']))
            year_balance = datetime.datetime.strptime(('%s-01-01' % (data['year'])), "%Y-%m-%d")
            open_balance_date = year_balance
            move_domain.append(('date', 'like', year))
            balance_domain.append(('date', '<', year_balance))
            from_to.append(['Year : %s' % data['year']])

        else:
            return {
                'waring': {
                    'title': 'Invalid Period',
                    'message': 'Select a valid period'
                }
            }
        printable_lines = []
        move_item = self.env['account.move.line'].search(move_domain)
        move_items = move_item.sorted(key=lambda k: (k.date, k.move_id.name), reverse=False)
        total_credit_in_period = 0.0
        total_debit_in_period = 0.0
        for item in move_items:
            total_credit_in_period += item.credit
            total_debit_in_period += item.debit
        balance_move_line = self.env['account.move.line'].search(balance_domain)
        total_credit_in_balance = 0.0
        total_debit_in_balance = 0.0
        for item in balance_move_line:
            total_credit_in_balance += item.credit
            total_debit_in_balance += item.debit

        docargs = {
            'docs': [printable_lines],
            'from_to': from_to,
            'total_credit_in_period':  total_credit_in_period,
            'total_debit_in_period': total_debit_in_period,
            'voucher_in_balance': total_credit_in_balance,
            'payments_in_balance': total_debit_in_balance,
            'open_balance_date': open_balance_date.strftime("%d-%m-%y"),
            'petty_cash_user': self.env['pettycash.fund'].browse(data['pettycash_user']),
            'move_items': move_items
        }
        return self.env['report'].render('account_petty_cash_ft.report_print_petty_cash_statement', docargs)

