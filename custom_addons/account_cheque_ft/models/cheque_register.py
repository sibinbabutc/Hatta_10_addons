# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning

BLANK_REQUIRED = {'blank': [('required', True), ('readonly', False)]}
DRAFT_EDITABLE = {'draft': [('readonly', False), ('required', True)]}


class ChequeMaster(models.AbstractModel):
    _name = 'cheque.abstract.register'

    def get_payee_name(self):
        if self.env.context.get('default_partner_id'):
            return self.env['res.partner'].browse(self.env.context.get('default_partner_id')).name

    state = fields.Selection([
        ('draft', 'Draft'),
        ('blank', 'Blank'),
        ('valid', 'Valid'),
        ('on_pdc', 'On PDC'),
        ('processed', 'Processed'),
        ('cancel', 'Cancelled')
    ], default='draft')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.user.company_id.currency_id.id)
    sl_no = fields.Char(string='Sl.No', readonly=True)
    cheque_no = fields.Char(string='Cheque Number', required=True)

    amount = fields.Monetary(string='Amount', readonly=True, states=BLANK_REQUIRED)
    partner_id = fields.Many2one('res.partner')
    payee_name = fields.Char('Payee', readonly=True, states=BLANK_REQUIRED, default=get_payee_name)
    issue_date = fields.Date(string='Issue Date', readonly=True, states=BLANK_REQUIRED)
    cheque_date = fields.Date(string='Cheque Date', readonly=True, states=BLANK_REQUIRED)

    category_id = fields.Selection([
        ('pdc', 'Post-Dated Cheque'),
        ('bgc', 'Bank Guarantee Cheque'),
        ('sc', 'Security Cheque')], 'Cheque Category', readonly=True)

    cheque_ref = fields.Char('Cheque Reference')
    description = fields.Text('Description')

    payment_id = fields.Many2one('account.payment', 'For Payment', readonly=True)

    @api.model
    def create(self, vals):
        vals.update({
            'sl_no': self.env['ir.sequence'].next_by_code('cheque_sl_no'),
            'state': 'blank'
        })
        res = super(ChequeMaster, self).create(vals)
        if res.payment_id:
            res.payment_id.payee_name = res.payee_name
        return res

    @api.multi
    def action_validate(self):
        for cheque in self:
            cheque.state = 'valid'

    @api.multi
    def processed(self):
        for cheque in self:
            cheque.state = 'processed'

    @api.multi
    def cancel_cheque(self, unlink=False):
        if self.state == 'blank':
            self.state = 'draft'
        self.state = 'cancel'
        # if unlink:
        #     self.unlink()

    @api.multi
    def set_to_blank(self):
        if self.state == 'cancel':
            self.write({'state': 'blank',
                        'payee_name': False,
                        'amount': 0.0,
                        'cheque_date': False,
                        'issue_date': False,
                        'payment_id': False})

    @api.multi
    def unlink(self):
        if self.state == 'blank':
            self.state = 'draft'
        return super(ChequeMaster, self).unlink()


class ChequeRegister(models.Model):
    _name = 'cheque.register'
    _inherit = ['cheque.abstract.register']
    _description = 'Cheque Register'
    _rec_name = 'cheque_no'
    _order = 'cheque_no'

    acc_num = fields.Many2one('account.journal', string='Account Number', domain=[('type', '=', 'bank')],
                              readonly=True, states=DRAFT_EDITABLE)
    bank_name = fields.Many2one('res.bank', string='Bank Name', readonly=True, states=DRAFT_EDITABLE)
    cheque_book_id = fields.Many2one('cheque.book', 'Cheque Book', readonly=True)

    _sql_constraints = [
        ('unique_cheque_no_per_acc_num', 'UNIQUE(cheque_no, bank_name, acc_num)', 'Duplicating Cheque Number.')
    ]

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, "%s (%s)" % (record.cheque_no, record.bank_name.name)))
        return result

    @api.onchange('acc_num')
    def onchange_acc_number(self):
        if self.acc_num:
            if not self.acc_num.bank_id:
                raise UserError("You haven't configure Bank Details. "
                                "Go to Accounting > Configurations > Bank Accounts")
            return {'value': {
                'bank_name': self.acc_num.bank_id,
            }}


EDIT_ON_DRAFT = {'draft': [('readonly', False)]}


class ChequeRegisterOut(models.Model):
    _name = 'cheque.register.out'
    _inherit = 'cheque.abstract.register'
    _description = 'Partner Cheque Register'
    _rec_name = 'cheque_no'
    _order = 'cheque_no'

    acc_num_out = fields.Char('Account Number')
    bank_name_out = fields.Many2one('res.bank.out', string='Bank Name')
    branch_id = fields.Many2one("res.bank.branch.out", string="Branch Name",
                                domain="[('bank_out_id', '=', bank_name_out)]")

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            result.append(
                (record.id,
                 "%s (%s)" % (record.cheque_no, record.bank_name_out.name)
                 ))
        return result

    @api.multi
    def create_and_link_cheque_out_id(self):
        active_model = self.env[self.env.context.get('active_model')]
        active_rec = active_model.browse(self.env.context.get('active_id'))
        active_rec.cheque_out_id = self.id
        return True


class ResBankOut(models.Model):
    _name = 'res.bank.out'
    _rec_name = 'name'
    _description = 'Outside Banks'

    name = fields.Char('Bank Name', required=True)
    branch_ids = fields.One2many('res.bank.branch.out', 'bank_out_id', string="Branches")


class ResBankBranchOut(models.Model):
    _name = 'res.bank.branch.out'
    _rec_name = 'name'
    _description = ''

    bank_out_id = fields.Many2one("res.bank.out", string="Bank")
    name = fields.Char('Branch Name', required=True)


class ChequeBook(models.Model):
    _name = 'cheque.book'
    _description = 'Cheque Books'
    _rec_name = 'cheque_book_ref'

    cheque_book_ref = fields.Char('Cheque Book Reference', required=True)
    acc_num = fields.Many2one('account.journal', string='Account Number', domain=[('type', '=', 'bank')],
                              required=True)
    bank_name = fields.Many2one('res.bank', string='Name of Bank', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('validated', 'Validated'),
        ('registered', 'Registered'),
        ('invalidate', 'Invalidated'),
        ('cancel', 'Cancelled')
    ], default='draft')
    cheque_no_from = fields.Char(string='From', required=True, readonly=True, states=EDIT_ON_DRAFT)
    cheque_no_to = fields.Char(string='Upto', required=True, readonly=True, states=EDIT_ON_DRAFT)

    no_of_cheques = fields.Integer('Cheque Quantity', compute='get_cheque_quantity')

    cheque_ids = fields.One2many('cheque.register', 'cheque_book_id', 'Cheques')

    _sql_constraints = [
        ('cheque_no_greater', 'check(cheque_no_to > cheque_no_from)',
         'Error ! Cheque No From must be smaller than Cheque No To .'),
        ('unique_cheque_book_ref', 'UNIQUE(cheque_book_ref)',
         'Same Cheque Book Reference already exists.')
    ]

    @api.depends('cheque_no_from', 'cheque_no_to')
    def get_cheque_quantity(self):
        for cheque in self:
            if cheque.cheque_no_from and cheque.cheque_no_to:
                cheque.no_of_cheques = abs(int(cheque.cheque_no_from) - int(cheque.cheque_no_to)) + 1

    @api.multi
    def invalidate(self):
        for cheque in self.cheque_ids:
            # if cheque.cheque_no in range(int(self.cheque_no_from), int(self.cheque_no_to)):
            if cheque.state != 'blank':
                raise UserError('You cannot Invalidate Cheque Book which have Non-Blank Cheques.')
        self.state = 'invalidate'

    @api.multi
    def unlink(self):
        if self.filtered(lambda x: x.state in ('account_cheque_ft', 'registered')):
            raise UserError(
                _('You cannot delete Registered Cheques.To delete Cheques Invalidate first'))
        for item in self.cheque_ids:
            item.unlink()
        return super(ChequeBook, self).unlink()

    @api.onchange('cheque_no_from')
    def onchange_cheque_no_from(self):
        self.cheque_no_to = self.cheque_no_from

    @api.onchange('acc_num')
    def onchange_acc_number(self):
        if self.acc_num:
            if not self.acc_num.bank_id:
                raise RedirectWarning("You haven't configure Bank Details. "
                                      "Go to Accounting > Configurations > Bank Accounts")
            self.bank_name = self.acc_num.bank_id

    @api.constrains('cheque_no_from', 'cheque_no_to')
    def cheque_book_sequence_constrain(self):
        if self.cheque_no_from and self.cheque_no_to and (self.cheque_no_from > self.cheque_no_to):
            raise UserError('Please check the Cheque Numbers Series you entered.')
        return True

    @api.multi
    def validate(self):
        if self.cheque_no_from and self.cheque_no_to and self.cheque_book_sequence_constrain():
            cheque_nums_to_create = []
            for i in range(int(self.cheque_no_from), int(self.cheque_no_to) + 1):
                cheque_nums_to_create.append(str(i).zfill(len(self.cheque_no_from)))
            duplicate = self.env['cheque.register'].search([
                ('cheque_no', 'in', cheque_nums_to_create),
                ('acc_num', '=', self.acc_num.id)
            ])
            if duplicate:
                raise ValidationError('This Cheque Book registration will create Duplicate Cheques.'
                                      'Please reconsider the series.')
            self.state = 'validated'
        else:
            raise ValidationError('Cheque Sl.No:Start No/End No Not Found')

    @api.multi
    def register_cheques(self):
        for i in range(int(self.cheque_no_from), int(self.cheque_no_to) + 1):
            cheques = self.env['cheque.register'].create({
                'acc_num': self.acc_num.id,
                'acc_num_out': self.acc_num.name,
                'bank_name': self.bank_name.id,
                'bank_name_out': self.bank_name.name,
                'cheque_no': str(i).zfill(len(self.cheque_no_from)),
                'cheque_book_id': self.id
            })
        self.state = 'registered'
        return cheques

    @api.multi
    def cancel_cheques(self):
        if self.cheque_ids:
            self.cheque_ids.cancel()
        self.state = 'cancel'
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': self._name,
            'res_id': self.id
        }

    @api.multi
    def cancel(self):
        if self.state == 'registered' and self.cheque_ids:
            action_id = self.env.ref('account_cheque_ft.action_server_cancel_cheques').id
            action = '%s&active_id=%s' % (action_id, self.id)
            raise RedirectWarning('Are you sure want cancel this Cheque Book and its related'
                                  'Cheque Leafs ?', action, 'Confirm and Continue')
        else:
            self.state = 'cancel'
