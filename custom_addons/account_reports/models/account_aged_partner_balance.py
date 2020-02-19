# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _, fields
from odoo.tools.misc import formatLang

import time
from odoo import api, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from datetime import datetime
from dateutil.relativedelta import relativedelta


class report_account_aged_partner(models.AbstractModel):
    _name = "account.aged.partner"
    _description = "Aged Partner Balances"

    def _format(self, value):
        if self.env.context.get('no_format'):
            return value
        currency_id = self.env.user.company_id.currency_id
        if currency_id.is_zero(value):
            # don't print -0.0 in reports
            value = abs(value)
        return formatLang(self.env, value, currency_obj=currency_id)

    @api.model
    def _lines(self, context, line_id=None):
        lines = []
        results, total, amls = self.env['report.account.report_agedpartnerbalance']._get_partner_move_lines(
            [self._context['account_type']], self._context['date_to'], 'posted', 30, self._context)
        for values in results:
            if line_id and values['partner_id'] != line_id:
                continue
            vals = {
                'id': values['partner_id'] and values['partner_id'] or -1,
                'name': values['name'],
                'level': 0 if values['partner_id'] else 2,
                'type': values['partner_id'] and 'partner_id' or 'line',
                'footnotes': context._get_footnotes('partner_id', values['partner_id']),
                'columns': [values['direction'], values['4'], values['3'], values['2'], values['1'], values['0'],
                            values['total']],
                'trust': values['trust'],
                'unfoldable': values['partner_id'] and True or False,
                'unfolded': values['partner_id'] and (values['partner_id'] in context.unfolded_partners.ids) or False,
            }
            vals['columns'] = map(self._format, vals['columns'])
            lines.append(vals)
            if values['partner_id'] in context.unfolded_partners.ids:
                for line in amls[values['partner_id']]:
                    aml = line['line']
                    vals = {
                        'id': aml.id,
                        'name': aml.move_id.name if aml.move_id.name else '/',
                        'move_id': aml.move_id.id,
                        'action': aml.get_model_id_and_name(),
                        'level': 1,
                        'type': 'move_line_id',
                        'footnotes': context._get_footnotes('move_line_id', aml.id),
                        'columns': [line['period'] == 6 - i and self._format(line['amount']) or '' for i in range(7)],
                    }
                    lines.append(vals)
                vals = {
                    'id': values['partner_id'],
                    'type': 'o_account_reports_domain_total',
                    'name': _('Total '),
                    'footnotes': self.env.context['context_id']._get_footnotes('o_account_reports_domain_total',
                                                                               values['partner_id']),
                    'columns': [values['direction'], values['4'], values['3'], values['2'], values['1'], values['0'],
                                values['total']],
                    'level': 1,
                }
                vals['columns'] = map(self._format, vals['columns'])
                lines.append(vals)
        if total and not line_id:
            total_line = {
                'id': 0,
                'name': _('Total'),
                'level': 0,
                'type': 'o_account_reports_domain_total',
                'footnotes': context._get_footnotes('o_account_reports_domain_total', 0),
                'columns': [total[6], total[4], total[3], total[2], total[1], total[0], total[5]],
            }
            total_line['columns'] = map(self._format, total_line['columns'])
            lines.append(total_line)
        return lines


class report_account_aged_receivable(models.AbstractModel):
    _name = "account.aged.receivable"
    _description = "Aged Receivable"
    _inherit = "account.aged.partner"

    @api.model
    def get_lines(self, context_id, line_id=None):
        if type(context_id) == int:
            context_id = self.env['account.context.aged.receivable'].search([['id', '=', context_id]])
        new_context = dict(self.env.context)
        new_context.update({
            'date_to': context_id.date_to,
            'context_id': context_id,
            'company_ids': context_id.company_ids.ids,
            'account_type': 'receivable',
            'analytic': True,
        })
        return self.with_context(new_context)._lines(context_id, line_id)

    @api.model
    def get_title(self):
        return _("Aged Receivable")

    @api.model
    def get_name(self):
        return 'aged_receivable'

    @api.model
    def get_report_type(self):
        return self.env.ref('account_reports.account_report_type_nothing')

    def get_template(self):
        return 'account_reports.report_financial'


class account_context_aged_receivable(models.TransientModel):
    _name = "account.context.aged.receivable"
    _description = "A particular context for the aged receivable"
    _inherit = "account.report.context.common"

    fold_field = 'unfolded_partners'
    unfolded_partners = fields.Many2many('res.partner', 'aged_receivable_context_to_partner', string='Unfolded lines')

    def get_report_obj(self):
        return self.env['account.aged.receivable']

    def get_columns_names(self):
        return [_("Not due on %s") % self.date_to, _("0 - 30"), _("30 - 60"), _("60 - 90"), _("90 - 120"), _("Older"),
                _("Total")]

    @api.multi
    def get_columns_types(self):
        return ["number", "number", "number", "number", "number", "number", "number"]


class report_account_aged_payable(models.AbstractModel):
    _name = "account.aged.payable"
    _description = "Aged Payable"
    _inherit = "account.aged.partner"

    @api.model
    def get_lines(self, context_id, line_id=None):
        if type(context_id) == int:
            context_id = self.env['account.context.aged.payable'].search([['id', '=', context_id]])
        new_context = dict(self.env.context)
        new_context.update({
            'date_to': context_id.date_to,
            'aged_balance': True,
            'context_id': context_id,
            'company_ids': context_id.company_ids.ids,
            'account_type': 'payable',
            'analytic': True,
            'hide_analytic_acc':True,
        })
        return self.with_context(new_context)._lines(context_id, line_id)

    @api.model
    def get_title(self):
        return _("Aged Payable")

    @api.model
    def get_name(self):
        return 'aged_payable'

    @api.model
    def get_report_type(self):
        return self.env.ref('account_reports.account_report_type_nothing')

    def get_template(self):
        return 'account_reports.report_financial'


class account_context_aged_payable(models.TransientModel):
    _name = "account.context.aged.payable"
    _description = "A particular context for the aged payable"
    _inherit = "account.report.context.common"

    fold_field = 'unfolded_partners'
    unfolded_partners = fields.Many2many('res.partner', 'aged_payable_context_to_partner', string='Unfolded lines')

    def get_report_obj(self):
        return self.env['account.aged.payable']

    def get_columns_names(self):
        return [_("Not due on %s") % self.date_to, _("0 - 30"), _("30 - 60"), _("60 - 90"), _("90 - 120"), _("Older"),
                _("Total")]

    @api.multi
    def get_columns_types(self):
        return ["number", "number", "number", "number", "number", "number", "number"]


class ReportAgedPartnerBalance(models.AbstractModel):
    _inherit = 'report.account.report_agedpartnerbalance'

    def _get_partner_move_lines(self, account_type, date_from, target_move, period_length, context=None):
        # This method can receive the context key 'include_nullified_amount' {Boolean}
        # Do an invoice and a payment and unreconcile. The amount will be nullified
        # By default, the partner wouldn't appear in this report.
        # The context key allow it to appear
        analytic_tag_ids = None
        if context and 'context_id' in context and 'analytic_tag_ids' in context['context_id']:
            analytic_tag_ids = context['context_id']['analytic_tag_ids']

        periods = {}
        start = datetime.strptime(date_from, "%Y-%m-%d")
        for i in range(5)[::-1]:
            stop = start - relativedelta(days=period_length)
            periods[str(i)] = {
                'name': (i != 0 and (str((5 - (i + 1)) * period_length) + '-' + str((5 - i) * period_length)) or (
                            '+' + str(4 * period_length))),
                'stop': start.strftime('%Y-%m-%d'),
                'start': (i != 0 and stop.strftime('%Y-%m-%d') or False),
            }
            start = stop - relativedelta(days=1)

        res = []
        total = []
        cr = self.env.cr
        user_company = self.env.user.company_id.id
        move_state = ['draft', 'posted']
        if target_move == 'posted':
            move_state = ['posted']
        arg_list = (tuple(move_state), tuple(account_type))
        # build the reconciliation clause to see what partner needs to be printed
        reconciliation_clause = '(l.reconciled IS FALSE)'
        cr.execute('SELECT debit_move_id, credit_move_id FROM account_partial_reconcile where create_date > %s',
                   (date_from,))
        reconciled_after_date = []
        for row in cr.fetchall():
            reconciled_after_date += [row[0], row[1]]
        if reconciled_after_date:
            reconciliation_clause = '(l.reconciled IS FALSE OR l.id IN %s)'
            arg_list += (tuple(reconciled_after_date),)
        arg_list += (date_from, user_company)
        query = '''
            SELECT DISTINCT l.partner_id, UPPER(res_partner.name)
            FROM account_move_line AS l left join res_partner on l.partner_id = res_partner.id, account_account, account_move am
            WHERE (l.account_id = account_account.id)
                AND (l.move_id = am.id)
                AND (am.state IN %s)
                AND (account_account.internal_type IN %s)
                AND ''' + reconciliation_clause + '''
                AND (l.date <= %s)
                AND l.company_id = %s
            ORDER BY UPPER(res_partner.name)'''
        cr.execute(query, arg_list)

        partners = cr.dictfetchall()
        # put a total of 0
        for i in range(7):
            total.append(0)

        # Build a string like (1,2,3) for easy use in SQL query
        partner_ids = [partner['partner_id'] for partner in partners if partner['partner_id']]
        lines = dict((partner['partner_id'] or False, []) for partner in partners)
        if not partner_ids:
            return [], [], []

        # This dictionary will store the not due amount of all partners
        undue_amounts = {}
        query = '''SELECT l.id
                FROM account_move_line AS l, account_account, account_move am
                WHERE (l.account_id = account_account.id) AND (l.move_id = am.id)
                    AND (am.state IN %s)
                    AND (account_account.internal_type IN %s)
                    AND (COALESCE(l.date_maturity,l.date) > %s)\
                    AND ((l.partner_id IN %s) OR (l.partner_id IS NULL))
                AND (l.date <= %s)
                AND l.company_id = %s'''
        cr.execute(query,
                   (tuple(move_state), tuple(account_type), date_from, tuple(partner_ids), date_from, user_company))
        aml_ids = cr.fetchall()
        aml_ids = aml_ids and [x[0] for x in aml_ids] or []
        for line in self.env['account.move.line'].browse(aml_ids):
            if analytic_tag_ids:
                in_line = [x for x in line.analytic_tag_ids.ids if x in analytic_tag_ids.ids]
                if len(in_line) > 0:
                    partner_id = line.partner_id.id or False
                    if partner_id not in undue_amounts:
                        undue_amounts[partner_id] = 0.0
                    line_amount = line.balance
                    if line.balance == 0:
                        continue
                    for partial_line in line.matched_debit_ids:
                        if partial_line.create_date[:10] <= date_from:
                            line_amount += partial_line.amount
                    for partial_line in line.matched_credit_ids:
                        if partial_line.create_date[:10] <= date_from:
                            line_amount -= partial_line.amount
                    if not self.env.user.company_id.currency_id.is_zero(line_amount):
                        undue_amounts[partner_id] += line_amount
                        lines[partner_id].append({
                            'line': line,
                            'amount': line_amount,
                            'period': 6,
                        })
            else:
                partner_id = line.partner_id.id or False
                if partner_id not in undue_amounts:
                    undue_amounts[partner_id] = 0.0
                line_amount = line.balance
                if line.balance == 0:
                    continue
                for partial_line in line.matched_debit_ids:
                    if partial_line.create_date[:10] <= date_from:
                        line_amount += partial_line.amount
                for partial_line in line.matched_credit_ids:
                    if partial_line.create_date[:10] <= date_from:
                        line_amount -= partial_line.amount
                if not self.env.user.company_id.currency_id.is_zero(line_amount):
                    undue_amounts[partner_id] += line_amount
                    lines[partner_id].append({
                        'line': line,
                        'amount': line_amount,
                        'period': 6,
                    })

        # Use one query per period and store results in history (a list variable)
        # Each history will contain: history[1] = {'<partner_id>': <partner_debit-credit>}
        history = []
        for i in range(5):
            args_list = (tuple(move_state), tuple(account_type), tuple(partner_ids),)
            dates_query = '(COALESCE(l.date_maturity,l.date)'

            if periods[str(i)]['start'] and periods[str(i)]['stop']:
                dates_query += ' BETWEEN %s AND %s)'
                args_list += (periods[str(i)]['start'], periods[str(i)]['stop'])
            elif periods[str(i)]['start']:
                dates_query += ' >= %s)'
                args_list += (periods[str(i)]['start'],)
            else:
                dates_query += ' <= %s)'
                args_list += (periods[str(i)]['stop'],)
            args_list += (date_from, user_company)

            query = '''SELECT l.id
                    FROM account_move_line AS l, account_account, account_move am
                    WHERE (l.account_id = account_account.id) AND (l.move_id = am.id)
                        AND (am.state IN %s)
                        AND (account_account.internal_type IN %s)
                        AND ((l.partner_id IN %s) OR (l.partner_id IS NULL))
                        AND ''' + dates_query + '''
                    AND (l.date <= %s)
                    AND l.company_id = %s'''
            cr.execute(query, args_list)
            partners_amount = {}
            aml_ids = cr.fetchall()
            aml_ids = aml_ids and [x[0] for x in aml_ids] or []
            for line in self.env['account.move.line'].browse(aml_ids):
                if analytic_tag_ids:
                    in_line = [x for x in line.analytic_tag_ids.ids if x in analytic_tag_ids.ids]
                    if len(in_line) > 0:
                        partner_id = line.partner_id.id or False
                        if partner_id not in partners_amount:
                            partners_amount[partner_id] = 0.0
                        line_amount = line.balance
                        if line.balance == 0:
                            continue
                        for partial_line in line.matched_debit_ids:
                            if partial_line.create_date[:10] <= date_from:
                                line_amount += partial_line.amount
                        for partial_line in line.matched_credit_ids:
                            if partial_line.create_date[:10] <= date_from:
                                line_amount -= partial_line.amount

                        if not self.env.user.company_id.currency_id.is_zero(line_amount):
                            partners_amount[partner_id] += line_amount
                            lines[partner_id].append({
                                'line': line,
                                'amount': line_amount,
                                'period': i + 1,
                            })
                else:
                    partner_id = line.partner_id.id or False
                    if partner_id not in partners_amount:
                        partners_amount[partner_id] = 0.0
                    line_amount = line.balance
                    if line.balance == 0:
                        continue
                    for partial_line in line.matched_debit_ids:
                        if partial_line.create_date[:10] <= date_from:
                            line_amount += partial_line.amount
                    for partial_line in line.matched_credit_ids:
                        if partial_line.create_date[:10] <= date_from:
                            line_amount -= partial_line.amount

                    if not self.env.user.company_id.currency_id.is_zero(line_amount):
                        partners_amount[partner_id] += line_amount
                        lines[partner_id].append({
                            'line': line,
                            'amount': line_amount,
                            'period': i + 1,
                        })
            history.append(partners_amount)

        for partner in partners:
            if partner['partner_id'] is None:
                partner['partner_id'] = False
            at_least_one_amount = False
            values = {}
            undue_amt = 0.0
            if partner['partner_id'] in undue_amounts:  # Making sure this partner actually was found by the query
                undue_amt = undue_amounts[partner['partner_id']]

            total[6] = total[6] + undue_amt
            values['direction'] = undue_amt
            if not float_is_zero(values['direction'], precision_rounding=self.env.user.company_id.currency_id.rounding):
                at_least_one_amount = True

            for i in range(5):
                during = False
                if partner['partner_id'] in history[i]:
                    during = [history[i][partner['partner_id']]]
                # Adding counter
                total[(i)] = total[(i)] + (during and during[0] or 0)
                values[str(i)] = during and during[0] or 0.0
                if not float_is_zero(values[str(i)], precision_rounding=self.env.user.company_id.currency_id.rounding):
                    at_least_one_amount = True
            values['total'] = sum([values['direction']] + [values[str(i)] for i in range(5)])
            ## Add for total
            total[(i + 1)] += values['total']
            values['partner_id'] = partner['partner_id']
            if partner['partner_id']:
                browsed_partner = self.env['res.partner'].browse(partner['partner_id'])
                values['name'] = browsed_partner.name and len(browsed_partner.name) >= 45 and browsed_partner.name[
                                                                                              0:40] + '...' or browsed_partner.name
                values['trust'] = browsed_partner.trust
            else:
                values['name'] = _('Unknown Partner')
                values['trust'] = False

            if at_least_one_amount or self._context.get('include_nullified_amount'):
                res.append(values)

        return res, total, lines
