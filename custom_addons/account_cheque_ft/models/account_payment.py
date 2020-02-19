# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools import english_number
from odoo.exceptions import UserError

PAY_METH_CODES = [
    'cheque_payment',
    'cheque_receipt',
    'cheque_pdc_payment',
    'cheque_pdc_receipt'
]
PAYMENT_METH_CODES = [
    'cheque_payment',
    'cheque_pdc_payment',
]
RECEIPT_METH_CODES = [
    'cheque_receipt',
    'cheque_pdc_receipt'
]

def amount_to_text_ae_in_cheque(number):
    number = '%.2f' % number
    units_name = ' '
    list = str(number).split('.')
    start_word = english_number(int(list[0]))
    end_word = english_number(int(list[1]))
    fils_name = 'Fils'

    return ' '.join(filter(None,
                           [start_word, units_name, (start_word or units_name) and (end_word or fils_name) and 'and',
                           fils_name, end_word]))

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


class AccountPaymentMethod(models.Model):
    _inherit = "account.payment.method"

    payment_method_type = fields.Selection([('normal', 'Normal'), ('delayed', 'Delayed')], default='normal')


class AccountChequePayment(models.Model):
    _inherit = "account.payment"

    bank_id = fields.Many2one('res.bank', related='journal_id.bank_id')

    cheque_id = fields.Many2one('cheque.register', 'Cheque No.',
                                domain="[('state', '=', 'blank'), ('bank_id', '=', bank_id)]",
                                ondelete='restrict')
    cheque_out_id = fields.Many2one('cheque.register.out', 'Cheque No.', domain=[('state', '=', 'blank')],
                                    ondelete='restrict')

    state = fields.Selection(selection_add=[('on_pdc', 'On PDC')])
    # state = fields.Selection([('draft', 'Draft'), ('posted', 'Posted'), ('sent', 'Sent'), ('reconciled', 'Reconciled'),('on_pdc', 'On PDC')], readonly=True, default='draft', copy=False, string="Status")
    #
    category_cheque_pdc_id = fields.Many2one('cheque.category.cheques', 'Post Dated Cheque', readonly=True)
    mature_date = fields.Date('Cheque Maturing Date')

    amount_in_words = fields.Char('Amount in Words', compute='get_amount_in_words', store=True)
    amount_in_words_cheque = fields.Char('Amount in Words', compute='get_amount_in_words_in_chque')
    payee_name = fields.Char('Cheque Issued to (Name)')

    @api.multi
    def set_to_draft(self):
        if self.move_id:
            to_reconcile = self.move_id.mapped('line_ids').filtered('reconciled')
            to_reconcile.remove_move_reconcile()
            self.move_id.unlink()
        if self.cheque_id:
            self.cheque_id.write({
                'payee_name': False,
                'amount': 0.0,
                'cheque_date': False,
                'state': 'blank',
                'payment_id': False
            })
        if self.cheque_out_id:
            self.cheque_out_id.write({
                'payee_name': False,
                'amount': 0.0,
                'cheque_date': False,
                'state': 'blank',
                'payment_id': False,
            })
        self.state = 'draft'
        self.move_name = False
        if self.category_cheque_pdc_id:
            self.category_cheque_pdc_id.write({
                'state': 'cancel'
            })

    @api.onchange('cheque_id')
    def onchange_cheque_id(self):
        if self.cheque_id and self.search(
                [('cheque_id', '=', self.cheque_id.id), ('state', 'in', ['draft'])]):
            self.cheque_id = False
            raise UserError('You have selected a Cheque, which has been already used for another Payment.'
                            'But not yet confirmed it')

    @api.onchange('partner_id')
    def onchange_partner_id_payee(self):
        if self.partner_id:
            self.payee_name = self.partner_id.name

    @api.depends('amount')
    def get_amount_in_words(self):
        for payment in self:
            payment.amount_in_words = amount_to_text_ae(payment.amount)

    @api.depends('amount')
    def get_amount_in_words_in_chque(self):
        for payment in self:
            payment.amount_in_words_cheque = amount_to_text_ae_in_cheque(payment.amount)

    @api.onchange('amount')
    def _onchange_amount(self):
        if hasattr(super(AccountChequePayment, self), '_onchange_amount'):
            super(AccountChequePayment, self)._onchange_amount()
        self.amount_in_words = amount_to_text_ae(self.amount)

    @api.onchange('payment_type', 'journal_id')
    def onchange_payment_type_journal(self):
        self.cheque_id = False
        if self.journal_id and self.journal_id.type == 'bank':
            if not self.journal_id.bank_id:
                raise UserError("You haven't configure Bank Details. "
                                "Go to Accounting > Configurations > Accounting > Journals")

    @api.multi
    def write(self, vals):
        if 'payment_method_id' in vals and self.payment_method_code in PAY_METH_CODES and self.cheque_id:
            raise UserError('Sorry You Cannot change Payment Method of this Payment,'
                            ' Because you already create a Cheque.')
        else:
            return super(AccountChequePayment, self).write(vals)

    @api.multi
    def create_category_cheque(self):
        category_cheque_o = self.env['cheque.category.cheques']
        return category_cheque_o.create({
            'payment_id': self.id,
            'category_id': 'pdc',
            'partner_id': self.partner_id.id,
            'reg_date': self.payment_date,
            'mature_date': self.mature_date,
            'cheque_amount': self.amount,
            'memo': self.communication,
            'cheque_id': self.cheque_id.id,
            'cheque_out_id': self.cheque_out_id.id,
            'cheque_no': self.cheque_id.cheque_no if self.cheque_id else (
                self.cheque_out_id.cheque_no if self.cheque_out_id else ' '),
            'cheque_type': 'company' if self.payment_method_code == 'cheque_pdc_payment' else 'partner',
            'cheque_ref': self.cheque_id.cheque_ref if self.cheque_id else(
                self.cheque_out_id.cheque_ref if self.cheque_out_id else ' '),
            'description': self.cheque_id.description if self.cheque_id else(
                self.cheque_out_id.description if self.cheque_out_id else ' '),
        })

    @api.multi
    def process_pdc_method(self):
        category_cheque_pdc_id = self.create_category_cheque()
        category_cheque_pdc_id.action_validate()
        self.update({
            'state': 'on_pdc',
            'category_cheque_pdc_id': category_cheque_pdc_id,
        })

    @api.multi
    def post_pdc(self):
        self.state = 'draft'
        return super(AccountChequePayment, self).post()

    @api.multi
    def post(self):
        if not self.cheque_id and self.payment_method_code in PAYMENT_METH_CODES:
            raise UserError('Without a Cheque Entry, You cannot validate this Payment')
        if not self.cheque_out_id and self.payment_method_code in RECEIPT_METH_CODES:
            raise UserError('Without a Cheque Entry, You cannot validate this Payment')
        if self.cheque_id:
            if self.cheque_id.state != 'blank':
                raise UserError('Sorry, This Cheque has been already used by another Payment.')
            self.cheque_id.write({
                'payee_name': self.payee_name,
                'amount': self.amount,
                'issue_date': self.payment_date,
                'cheque_date': self.mature_date if (
                    self.mature_date and self.payment_method_code in ['cheque_pdc_payment',
                                                                      'cheque_pdc_receipt']) else self.payment_date,
                'payment_id': self.id
            })
            self.cheque_id.action_validate()
        elif self.cheque_out_id:
            if self.cheque_out_id.state != 'blank':
                raise UserError('Sorry, This Cheque has been already used by another Payment.')
            self.cheque_out_id.write({
                'payee_name': self.payee_name,
                'amount': self.amount,
                'issue_date': self.payment_date,
                'cheque_date': self.mature_date if (
                    self.mature_date and self.payment_method_code in ['cheque_pdc_payment',
                                                                      'cheque_pdc_receipt']) else self.payment_date,
                'payment_id': self.id
            })
            self.cheque_out_id.action_validate()
        if self.payment_method_code in ['cheque_pdc_payment', 'cheque_pdc_receipt']:
            return self.process_pdc_method()
        res = super(AccountChequePayment, self).post()
        return res

    @api.multi
    def unlink(self):
        for record in self:
            cheque_id = record.cheque_id
            super(AccountChequePayment, record).unlink()
            if cheque_id and cheque_id.state == 'blank':
                cheque_id.cancel_cheque()
        return True

    @api.multi
    def print_cheque(self):
        if not self.cheque_id:
            raise UserError('You cannot print Cheque without creating one.')
        else:
            return {
                'name': _("Cheque Print"),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'view_id': self.env.ref('account_cheque_ft.cheque_report_wizard_report_wizard').id,
                'view_type': 'form',
                'res_model': 'cheque.report.wizard',
                'target': 'new',
                'context': {
                    'default_payment_id': self.id
                }
            }
