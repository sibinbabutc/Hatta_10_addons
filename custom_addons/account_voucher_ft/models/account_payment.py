from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import english_number
from odoo.addons.account.models.account_payment import account_payment


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


DRAFT_EDITONLY = {'draft': [('readonly', False)]}


class AccountPayment(account_payment):
    @api.multi
    def post(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(
                    _("Only a draft payment can be posted. Trying to post a payment in state %s.") % rec.state)

            if any(inv.state != 'open' for inv in rec.invoice_ids):
                raise ValidationError(_("The payment cannot be processed because the invoice is not open!"))

            # Use the right sequence to set the name
            if rec.payment_type == 'transfer':
                sequence_code = 'account.payment.transfer'
            else:
                if rec.partner_type == 'customer':
                    if rec.payment_type == 'inbound':
                        sequence_code = 'account.payment.customer.invoice'
                    if rec.payment_type == 'outbound':
                        sequence_code = 'account.payment.customer.refund'
                if rec.partner_type == 'supplier':
                    if rec.payment_type == 'inbound':
                        sequence_code = 'account.payment.supplier.refund'
                    if rec.payment_type == 'outbound':
                        sequence_code = 'account.payment.supplier.invoice'
            if rec.name == 'Draft Payment':
                rec.name = self.env['ir.sequence'].with_context(ir_sequence_date=rec.payment_date).next_by_code(
                    sequence_code) + ' (%s)' % self.journal_id.code

            # Create the journal entry
            amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)
            move = rec._create_payment_entry(amount)

            # In case of a transfer, the first journal entry created debited the source liquidity account and credited
            # the transfer account. Now we debit the transfer account and credit the destination liquidity account.
            if rec.payment_type == 'transfer':
                transfer_credit_aml = move.line_ids.filtered(
                    lambda r: r.account_id == rec.company_id.transfer_account_id)
                transfer_debit_aml = rec._create_transfer_entry(amount)
                (transfer_credit_aml + transfer_debit_aml).reconcile()

            rec.write({'state': 'posted', 'move_name': move.name, 'checked_by': rec.env.user.name})


class AccountPaymentCustom(models.Model):
    _name = 'account.payment'
    _inherit = ['account.payment', 'mail.thread', 'ir.needaction_mixin']

    have_lines = fields.Boolean()
    have_bills = fields.Boolean()

    partner_id = fields.Many2one('res.partner', string='Partner', ondelete='restrict')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Confirmed'),
        ('accounted', 'Posted'),
        ('sent', 'Sent'),
        ('on_pdc', 'On PDC'),
        ('reconciled', 'Reconciled')], track_visibility='onchange', readonly=True, default='draft', copy=False, string="Status")

    move_id = fields.Many2one('account.move')
    transfer_move_id = fields.Many2one('account.move')

    voucher_lines = fields.One2many('account.payment.line', 'payment_id', readonly=True,
                                    states={'draft': [('readonly', False)]})

    amount_in_words = fields.Char('Amount in Words', compute='get_amount_in_words', store=True)

    transfer_bank_name = fields.Char(string="Bank", states=DRAFT_EDITONLY, readonly=True)
    transfer_ref = fields.Char(string="Transfer Ref", states=DRAFT_EDITONLY, readonly=True)
    transfer_acc_no = fields.Char(string="Account No", states=DRAFT_EDITONLY, readonly=True)

    prepared_by = fields.Char('Prepared By', default=lambda s: s.env.user.name, readonly=True)
    checked_by = fields.Char('Checked By', readonly=True)
    passed_by = fields.Char('Passed By', readonly=True)

    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values and self.state == 'draft':
            return 'account_voucher_ft.ft_account_payment_draft'
        elif 'state' in init_values and self.state == 'posted':
            return 'account_voucher_ft.ft_account_payment_posted'
        elif 'state' in init_values and self.state == 'accounted':
            return 'account_voucher_ft.ft_account_payment_accounted'
        elif 'state' in init_values and self.state == 'sent':
            return 'account_voucher_ft.ft_account_payment_sent'
        elif 'state' in init_values and self.state == 'on_pdc':
            return 'account_voucher_ft.ft_account_payment_on_pdc'
        elif 'state' in init_values and self.state == 'reconciled':
            return 'account_voucher_ft.ft_account_payment_reconciled'
        return super(AccountPaymentCustom, self)._track_subtype(init_values)

    @api.multi
    def print_internal_transfer_pv(self):
        self.ensure_one()
        return self.env['report'].get_action(self, 'account_voucher_ft.report_internal_transfer_payment')

    def _get_move_vals(self, journal=None):
        """ Return dict to create the payment move
        """
        journal = journal or self.journal_id
        if not journal.sequence_id:
            raise UserError(_('Configuration Error !'),
                            _('The journal %s does not have a sequence, please specify one.') % journal.name)
        if not journal.sequence_id.active:
            raise UserError(_('Configuration Error !'), _('The sequence of journal %s is deactivated.') % journal.name)
        # name = self.move_name or journal.with_context(ir_sequence_date=self.payment_date).sequence_id.next_by_id()
        name = self.name
        return {
            'name': name,
            'date': self.mature_date if (
                    self.mature_date and self.payment_method_code in ['cheque_pdc_payment',
                                                                      'cheque_pdc_receipt']) else self.payment_date,
            'ref': self.communication or '',
            'company_id': self.company_id.id,
            'journal_id': journal.id,
        }

    @api.onchange('have_bills')
    def onchange_invoice_ids(self):
        if not self.have_bills and self.invoice_ids:
            self.invoice_ids = False

    @api.depends('amount')
    def get_amount_in_words(self):
        for payment in self:
            payment.amount_in_words = amount_to_text_ae(payment.amount)

    @api.onchange('voucher_lines', 'invoice_ids')
    def with_lines(self):
        if not self.have_bills and not self.have_lines:
            return {}
        amount = 0.0
        if self.have_bills:
            for item in self.invoice_ids:
                amount += item.residual

        if self.have_lines:
            for line in self.voucher_lines:
                amount += line.line_amount
        return {'value': {'amount': amount}}

    @api.onchange('have_lines')
    def onchange_have_line(self):
        if not self.have_lines and self.voucher_lines:
            self.voucher_lines = [(5, 0, False)]

    @api.multi
    def account_post(self):
        if self.move_id:
            self.move_id.post()
        if self.payment_type == 'transfer':
            self.transfer_move_id.post()
        self.state = 'accounted'
        self.passed_by = self.env.user.name

    @api.multi
    def print_voucher(self):
        return self.env['report'].get_action(self, 'account_voucher_ft.report_voucher')

    def _get_shared_move_line_vals_for_lines(self, debit, credit, amount_currency, move_id):
        return {
            'partner_id': self.partner_id.id,
            'invoice_id': False,
            'move_id': move_id,
            'debit': debit,
            'credit': credit,
            'amount_currency': amount_currency or False,
        }

    def _get_counterpart_move_line_vals_for_lines(self, line):
        res = self._get_counterpart_move_line_vals(invoice=False)
        res.update({
            'account_id': line.account_id.id,
            'name': line.name if line.name else ''
        })
        return res

    def _create_payment_entry(self, amount):

        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        invoice_currency = False
        if self.invoice_ids and all([x.currency_id == self.invoice_ids[0].currency_id for x in self.invoice_ids]):
            # if all the invoices selected share the same currency, record the paiement in that currency too
            invoice_currency = self.invoice_ids[0].currency_id
        debit, credit, amount_currency, currency_id = aml_obj.with_context(date=self.payment_date) \
            .compute_amount_fields(amount, self.currency_id, self.company_id.currency_id, invoice_currency)

        move = self.env['account.move'].create(self._get_move_vals())
        line_total = 0

        if self.have_lines and self.voucher_lines:
            for line in self.voucher_lines:
                # Write line corresponding to payment lines
                line_amount = line.line_amount * (self.payment_type in ('outbound', 'transfer') and 1 or -1)
                line_debit, line_credit, amount_currency, currency_id = aml_obj.with_context(
                    date=self.payment_date).compute_amount_fields(line_amount, self.currency_id,
                                                                  self.company_id.currency_id,
                                                                  invoice_currency)
                counterpart_aml_dict = self._get_shared_move_line_vals_for_lines(line_debit, line_credit,
                                                                                 amount_currency, move.id)
                counterpart_aml_dict.update(self._get_counterpart_move_line_vals_for_lines(line))
                counterpart_aml_dict.update({'currency_id': currency_id})
                counterpart_aml = aml_obj.create(counterpart_aml_dict)
                line_total += line_amount
        if not self.voucher_lines and self.have_lines:
            self.have_lines = False
        if self.have_bills and self.invoice_ids:
            # Write line corresponding to invoice payment
            line_amount = (amount - line_total)
            line_debit, line_credit, amount_currency, currency_id = aml_obj.with_context(
                date=self.payment_date).compute_amount_fields(line_amount, self.currency_id,
                                                              self.company_id.currency_id,
                                                              invoice_currency)

            counterpart_aml_dict = self._get_shared_move_line_vals(line_debit, line_credit, amount_currency, move.id,
                                                                   False)
            counterpart_aml_dict.update(self._get_counterpart_move_line_vals(self.invoice_ids))
            counterpart_aml_dict.update({'currency_id': currency_id})
            counterpart_aml = aml_obj.create(counterpart_aml_dict)
            self.invoice_ids.register_payment(counterpart_aml)

        if not self.invoice_ids and self.have_bills:
            self.have_bills = False

        if not (self.have_lines or self.have_bills):
            counterpart_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, move.id, False)
            counterpart_aml_dict.update(self._get_counterpart_move_line_vals(self.invoice_ids))
            counterpart_aml_dict.update({'currency_id': currency_id})
            counterpart_aml = aml_obj.create(counterpart_aml_dict)

        # Reconcile with the invoices
        if self.payment_difference_handling == 'reconcile' and self.payment_difference:
            writeoff_line = self._get_shared_move_line_vals(0, 0, 0, move.id, False)
            amount_currency_wo, currency_id = aml_obj.with_context(date=self.payment_date).compute_amount_fields(
                self.payment_difference, self.currency_id, self.company_id.currency_id, invoice_currency)[2:]
            # the writeoff debit and credit must be computed from the invoice residual in company currency
            # minus the payment amount in company currency, and not from the payment difference in the payment currency
            # to avoid loss of precision during the currency rate computations. See revision 20935462a0cabeb45480ce70114ff2f4e91eaf79 for a detailed example.
            total_residual_company_signed = sum(invoice.residual_company_signed for invoice in self.invoice_ids)
            total_payment_company_signed = self.currency_id.with_context(date=self.payment_date).compute(self.amount,
                                                                                                         self.company_id.currency_id)
            if self.invoice_ids[0].type in ['in_invoice', 'out_refund']:
                amount_wo = total_payment_company_signed - total_residual_company_signed
            else:
                amount_wo = total_residual_company_signed - total_payment_company_signed
            # Align the sign of the secondary currency writeoff amount with the sign of the writeoff
            # amount in the company currency
            if amount_wo > 0:
                debit_wo = amount_wo
                credit_wo = 0.0
                amount_currency_wo = abs(amount_currency_wo)
            else:
                debit_wo = 0.0
                credit_wo = -amount_wo
                amount_currency_wo = -abs(amount_currency_wo)
            writeoff_line['name'] = _('Counterpart')
            writeoff_line['account_id'] = self.writeoff_account_id.id
            writeoff_line['debit'] = debit_wo
            writeoff_line['credit'] = credit_wo
            writeoff_line['amount_currency'] = amount_currency_wo
            writeoff_line['currency_id'] = currency_id
            writeoff_line = aml_obj.create(writeoff_line)
            if counterpart_aml['debit']:
                counterpart_aml['debit'] += credit_wo - debit_wo
            if counterpart_aml['credit']:
                counterpart_aml['credit'] += debit_wo - credit_wo
            counterpart_aml['amount_currency'] -= amount_currency_wo
        self.invoice_ids.register_payment(counterpart_aml)

        if not self.currency_id != self.company_id.currency_id:
            amount_currency = 0
        liquidity_aml_dict = self._get_shared_move_line_vals(credit, debit, -amount_currency, move.id, False)
        liquidity_aml_dict.update(self._get_liquidity_move_line_vals(-amount))
        aml_obj.create(liquidity_aml_dict)

        self.move_id = move
        return move

    def _create_transfer_entry(self, amount):
        """ Create the journal entry corresponding to the 'incoming money' part of an internal transfer, return the reconciliable move line
        """
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        debit, credit, amount_currency, dummy = aml_obj.with_context(date=self.payment_date).compute_amount_fields(
            amount, self.currency_id, self.company_id.currency_id)
        amount_currency = self.destination_journal_id.currency_id and self.currency_id.with_context(
            date=self.payment_date).compute(amount, self.destination_journal_id.currency_id) or 0

        dst_move = self.env['account.move'].create(self._get_move_vals(self.destination_journal_id))

        dst_liquidity_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, dst_move.id)
        dst_liquidity_aml_dict.update({
            'name': _('Transfer from %s') % self.journal_id.name,
            'account_id': self.destination_journal_id.default_credit_account_id.id,
            'currency_id': self.destination_journal_id.currency_id.id,
            'payment_id': self.id,
            'journal_id': self.destination_journal_id.id})
        aml_obj.create(dst_liquidity_aml_dict)

        transfer_debit_aml_dict = self._get_shared_move_line_vals(credit, debit, 0, dst_move.id)
        transfer_debit_aml_dict.update({
            'name': self.name,
            'payment_id': self.id,
            'account_id': self.company_id.transfer_account_id.id,
            'journal_id': self.destination_journal_id.id})
        if self.currency_id != self.company_id.currency_id:
            transfer_debit_aml_dict.update({
                'currency_id': self.currency_id.id,
                'amount_currency': -self.amount,
            })
        transfer_debit_aml = aml_obj.create(transfer_debit_aml_dict)
        self.transfer_move_id = dst_move
        return transfer_debit_aml

    @api.multi
    def set_to_draft(self):
        if self.payment_type == 'transfer':
            aml_ids = (self.move_id + self.transfer_move_id).mapped('line_ids')
            aml_ids.remove_move_reconcile()
            self.transfer_move_id.unlink()
        return super(AccountPaymentCustom, self).set_to_draft()

    # send voucher with cheque details
    @api.multi
    def action_send_pv_cheque_email(self):
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = \
            ir_model_data.get_object_reference('account_voucher_ft', 'mail_template_data_email_pv_with_cheques')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'account.payment',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }


class AccountPaymentLine(models.Model):
    _name = 'account.payment.line'
    _description = 'Payment Lines'

    name = fields.Char(string='Description')
    payment_id = fields.Many2one('account.payment', 'Voucher', required=1, ondelete='cascade')

    account_id = fields.Many2one('account.account', string='Account',
                                 required=True, domain=[('deprecated', '=', False)],
                                 help="The income or expense account related to the selected product.")
    company_id = fields.Many2one('res.company', related='payment_id.company_id', string='Company', store=True,
                                 readonly=True)
    currency_id = fields.Many2one('res.currency', default=lambda s: s.payment_id.currency_id)
    line_amount = fields.Float('Amount', required=True)
    asset_id = fields.Many2one('account.asset.asset', string='Asset')


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    def process_reconciliation(self, counterpart_aml_dicts=None, payment_aml_rec=None, new_aml_dicts=None):
        """ Match statement lines with existing payments (eg. checks) and/or payables/receivables (eg. invoices and refunds) and/or new move lines (eg. write-offs).
            If any new journal item needs to be created (via new_aml_dicts or counterpart_aml_dicts), a new journal entry will be created and will contain those
            items, as well as a journal item for the bank statement line.
            Finally, mark the statement line as reconciled by putting the matched moves ids in the column journal_entry_ids.

            :param self: browse collection of records that are supposed to have no accounting entries already linked.
            :param (list of dicts) counterpart_aml_dicts: move lines to create to reconcile with existing payables/receivables.
                The expected keys are :
                - 'name'
                - 'debit'
                - 'credit'
                - 'move_line'
                    # The move line to reconcile (partially if specified debit/credit is lower than move line's credit/debit)

            :param (list of recordsets) payment_aml_rec: recordset move lines representing existing payments (which are already fully reconciled)

            :param (list of dicts) new_aml_dicts: move lines to create. The expected keys are :
                - 'name'
                - 'debit'
                - 'credit'
                - 'account_id'
                - (optional) 'tax_ids'
                - (optional) Other account.move.line fields like analytic_account_id or analytics_id

            :returns: The journal entries with which the transaction was matched. If there was at least an entry in counterpart_aml_dicts or new_aml_dicts, this list contains
                the move created by the reconciliation, containing entries for the statement.line (1), the counterpart move lines (0..*) and the new move lines (0..*).
        """
        counterpart_aml_dicts = counterpart_aml_dicts or []
        payment_aml_rec = payment_aml_rec or self.env['account.move.line']
        new_aml_dicts = new_aml_dicts or []

        aml_obj = self.env['account.move.line']

        company_currency = self.journal_id.company_id.currency_id
        statement_currency = self.journal_id.currency_id or company_currency
        st_line_currency = self.currency_id or statement_currency

        counterpart_moves = self.env['account.move']

        # Check and prepare received data
        if any(rec.statement_id for rec in payment_aml_rec):
            raise UserError(_('A selected move line was already reconciled.'))
        for aml_dict in counterpart_aml_dicts:
            if aml_dict['move_line'].reconciled:
                raise UserError(_('A selected move line was already reconciled.'))
            if isinstance(aml_dict['move_line'], (int, long)):
                aml_dict['move_line'] = aml_obj.browse(aml_dict['move_line'])
        for aml_dict in (counterpart_aml_dicts + new_aml_dicts):
            if aml_dict.get('tax_ids') and aml_dict['tax_ids'] and isinstance(aml_dict['tax_ids'][0], (int, long)):
                # Transform the value in the format required for One2many and Many2many fields
                aml_dict['tax_ids'] = map(lambda id: (4, id, None), aml_dict['tax_ids'])
        if any(line.journal_entry_ids for line in self):
            raise UserError(_('A selected statement line was already reconciled with an account move.'))

        # Fully reconciled moves are just linked to the bank statement
        total = self.amount
        for aml_rec in payment_aml_rec:
            total -= aml_rec.debit-aml_rec.credit
            aml_rec.with_context(check_move_validity=False).write({'statement_id': self.statement_id.id})
            aml_rec.move_id.write({'statement_line_id': self.id})
            counterpart_moves = (counterpart_moves | aml_rec.move_id)

        # Create move line(s). Either matching an existing journal entry (eg. invoice), in which
        # case we reconcile the existing and the new move lines together, or being a write-off.
        if counterpart_aml_dicts or new_aml_dicts:
            st_line_currency = self.currency_id or statement_currency
            st_line_currency_rate = self.currency_id and (self.amount_currency / self.amount) or False

            # Create the move
            self.sequence = self.statement_id.line_ids.ids.index(self.id) + 1
            move_vals = self._prepare_reconciliation_move(self.statement_id.name)
            move = self.env['account.move'].create(move_vals)
            counterpart_moves = (counterpart_moves | move)

            # Create The payment
            payment = self.env['account.payment']
            if abs(total)>0.00001:
                partner_id = self.partner_id and self.partner_id.id or False
                partner_type = False
                sequence_code = False
                if partner_id:
                    if total < 0:
                        partner_type = 'supplier'
                        if total > 0:
                            sequence_code = 'account.payment.supplier.refund'
                        else:
                            sequence_code = 'account.payment.supplier.invoice'
                    else:
                        partner_type = 'customer'
                        if total > 0:
                            sequence_code = 'account.payment.customer.invoice'
                        else:
                            sequence_code = 'account.payment.customer.refund'

                payment_methods = (total>0) and self.journal_id.inbound_payment_method_ids or self.journal_id.outbound_payment_method_ids
                currency = self.journal_id.currency_id or self.company_id.currency_id
                payment = self.env['account.payment'].create({
                    'payment_method_id': payment_methods and payment_methods[0].id or False,
                    'payment_type': total >0 and 'inbound' or 'outbound',
                    'partner_id': self.partner_id and self.partner_id.id or False,
                    'partner_type': partner_type,
                    'journal_id': self.statement_id.journal_id.id,
                    'payment_date': self.date,
                    'state': 'reconciled',
                    'currency_id': currency.id,
                    'amount': abs(total),
                    'communication': self._get_communication(payment_methods[0] if payment_methods else False),
                    'name': self.env['ir.sequence'].with_context(ir_sequence_date=self.date).next_by_code(sequence_code)
                })

            # Complete dicts to create both counterpart move lines and write-offs
            to_create = (counterpart_aml_dicts + new_aml_dicts)
            ctx = dict(self._context, date=self.date)
            for aml_dict in to_create:
                aml_dict['move_id'] = move.id
                aml_dict['partner_id'] = self.partner_id.id
                aml_dict['statement_id'] = self.statement_id.id
                if st_line_currency.id != company_currency.id:
                    aml_dict['amount_currency'] = aml_dict['debit'] - aml_dict['credit']
                    aml_dict['currency_id'] = st_line_currency.id
                    if self.currency_id and statement_currency.id == company_currency.id and st_line_currency_rate:
                        # Statement is in company currency but the transaction is in foreign currency
                        aml_dict['debit'] = company_currency.round(aml_dict['debit'] / st_line_currency_rate)
                        aml_dict['credit'] = company_currency.round(aml_dict['credit'] / st_line_currency_rate)
                    elif self.currency_id and st_line_currency_rate:
                        # Statement is in foreign currency and the transaction is in another one
                        aml_dict['debit'] = statement_currency.with_context(ctx).compute(aml_dict['debit'] / st_line_currency_rate, company_currency)
                        aml_dict['credit'] = statement_currency.with_context(ctx).compute(aml_dict['credit'] / st_line_currency_rate, company_currency)
                    else:
                        # Statement is in foreign currency and no extra currency is given for the transaction
                        aml_dict['debit'] = st_line_currency.with_context(ctx).compute(aml_dict['debit'], company_currency)
                        aml_dict['credit'] = st_line_currency.with_context(ctx).compute(aml_dict['credit'], company_currency)
                elif statement_currency.id != company_currency.id:
                    # Statement is in foreign currency but the transaction is in company currency
                    prorata_factor = (aml_dict['debit'] - aml_dict['credit']) / self.amount_currency
                    aml_dict['amount_currency'] = prorata_factor * self.amount
                    aml_dict['currency_id'] = statement_currency.id

            # Create write-offs
            # When we register a payment on an invoice, the write-off line contains the amount
            # currency if all related invoices have the same currency. We apply the same logic in
            # the manual reconciliation.
            counterpart_aml = self.env['account.move.line']
            for aml_dict in counterpart_aml_dicts:
                counterpart_aml |= aml_dict.get('move_line', self.env['account.move.line'])
            new_aml_currency = False
            if counterpart_aml\
                    and len(counterpart_aml.mapped('currency_id')) == 1\
                    and counterpart_aml[0].currency_id\
                    and counterpart_aml[0].currency_id != company_currency:
                new_aml_currency = counterpart_aml[0].currency_id
            for aml_dict in new_aml_dicts:
                aml_dict['payment_id'] = payment and payment.id or False
                if new_aml_currency and not aml_dict.get('currency_id'):
                    aml_dict['currency_id'] = new_aml_currency.id
                    aml_dict['amount_currency'] = company_currency.with_context(ctx).compute(aml_dict['debit'] - aml_dict['credit'], new_aml_currency)
                aml_obj.with_context(check_move_validity=False, apply_taxes=True).create(aml_dict)

            # Create counterpart move lines and reconcile them
            for aml_dict in counterpart_aml_dicts:
                if aml_dict['move_line'].partner_id.id:
                    aml_dict['partner_id'] = aml_dict['move_line'].partner_id.id
                aml_dict['account_id'] = aml_dict['move_line'].account_id.id
                aml_dict['payment_id'] = payment and payment.id or False

                counterpart_move_line = aml_dict.pop('move_line')
                if counterpart_move_line.currency_id and counterpart_move_line.currency_id != company_currency and not aml_dict.get('currency_id'):
                    aml_dict['currency_id'] = counterpart_move_line.currency_id.id
                    aml_dict['amount_currency'] = company_currency.with_context(ctx).compute(aml_dict['debit'] - aml_dict['credit'], counterpart_move_line.currency_id)
                new_aml = aml_obj.with_context(check_move_validity=False).create(aml_dict)

                (new_aml | counterpart_move_line).reconcile()

            # Balance the move
            st_line_amount = -sum([x.balance for x in move.line_ids])
            aml_dict = self._prepare_reconciliation_move_line(move, st_line_amount)
            aml_dict['payment_id'] = payment and payment.id or False
            aml_obj.with_context(check_move_validity=False).create(aml_dict)

            move.post()
            #record the move name on the statement line to be able to retrieve it in case of unreconciliation
            self.write({'move_name': move.name})
            payment.write({'payment_reference': move.name})
        elif self.move_name:
            raise UserError(_('Operation not allowed. Since your statement line already received a number, you cannot reconcile it entirely with existing journal entries otherwise it would make a gap in the numbering. You should book an entry and make a regular revert of it in case you want to cancel it.'))
        counterpart_moves.assert_balanced()
        return counterpart_moves
