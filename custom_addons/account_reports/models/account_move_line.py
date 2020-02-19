# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools.safe_eval import safe_eval


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = "account.move.line"

    expected_pay_date = fields.Date('Expected Payment Date', help="Expected payment date as manually set through the customer statement (e.g: if you had the customer on the phone and want to remember the date he promised he would pay)")
    internal_note = fields.Text('Internal Note', help="Note you can set through the customer statement about a receivable journal item")
    next_action_date = fields.Date('Next Action Date', help="Date where the next action should be taken for a receivable item. Usually, automatically set when sending reminders through the customer statement.")

    @api.multi
    def get_model_id_and_name(self):
        """Function used to display the right action on journal items on dropdown lists, in reports like general ledger"""
        if self.statement_id:
            return ['account.bank.statement', self.statement_id.id, _('View Bank Statement'), False]
        if self.payment_id:
            return ['account.payment', self.payment_id.id, _('View Payment'), False]
        if self.invoice_id:
            view_id = self.invoice_id.get_formview_id()
            return ['account.invoice', self.invoice_id.id, _('View Invoice'), view_id]
        return ['account.move', self.move_id.id, _('View Move'), False]

    @api.multi
    def write_blocked(self, blocked):
        """ This function is used to change the 'blocked' status of an aml.
            You need to be able to change it even if the aml is locked by the lock date
            (this function is used in the customer statements) """
        return self.with_context(check_move_validity=False).write({'blocked': blocked})

    @api.model
    def _query_get(self, domain=None):
        context = dict(self._context or {})
        domain = domain and safe_eval(str(domain)) or []

        date_field = 'date'
        if context.get('aged_balance'):
            date_field = 'date_maturity'
        if context.get('date_to'):
            domain += [(date_field, '<=', context['date_to'])]
        if context.get('date_from'):
            if not context.get('strict_range'):
                domain += ['|', (date_field, '>=', context['date_from']), ('account_id.user_type_id.include_initial_balance', '=', True)]
            elif context.get('initial_bal'):
                domain += [(date_field, '<', context['date_from'])]
            else:
                domain += [(date_field, '>=', context['date_from'])]

        if context.get('journal_ids'):
            domain += [('journal_id', 'in', context['journal_ids'])]

        if context.get('account_ids'):
            domain += [('account_id', 'in', context['account_ids'])]

        state = context.get('state')
        if state and state.lower() != 'all':
            domain += [('move_id.state', '=', state)]

        if context.get('company_id'):
            domain += [('company_id', '=', context['company_id'])]

        if 'company_ids' in context:
            domain += [('company_id', 'in', context['company_ids'])]

        if context.get('reconcile_date'):
            domain += ['|', ('reconciled', '=', False), '|', ('matched_debit_ids.create_date', '>', context['reconcile_date']), ('matched_credit_ids.create_date', '>', context['reconcile_date'])]

        if context.get('account_tag_ids'):
            domain += [('account_id.tag_ids', 'in', context['account_tag_ids'].ids)]

        if context.get('analytic_tag_ids'):
            domain += ['|', ('analytic_account_id.tag_ids', 'in', context['analytic_tag_ids'].ids), ('analytic_tag_ids', 'in', context['analytic_tag_ids'].ids)]

        if context.get('analytic_account_ids'):
            domain += [('analytic_account_id', 'in', context['analytic_account_ids'].ids)]

        where_clause = ""
        where_clause_params = []
        tables = ''
        if domain:
            query = self._where_calc(domain)
            tables, where_clause, where_clause_params = query.get_sql()
        return tables, where_clause, where_clause_params
