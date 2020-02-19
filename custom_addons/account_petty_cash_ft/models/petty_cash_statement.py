from odoo import api, fields, models


# class AccountReportContextCommon(models.TransientModel):
#     _inherit = "account.report.context.common"
#
#     def _report_model_to_report_context(self):
#         res = super(AccountReportContextCommon, self)._report_model_to_report_context()
#         res.update({
#             'account.pettycash.statement': 'account.context.pettycash.statement',
#         })
#         return res


# class ReportAccountPettyCashStatement(models.AbstractModel):
#     _name = 'account.pettycash.statement'
#     _inherit = "account.general.ledger"
#     _description = "Petty Cash Statement Report"
#
#
# class AccountContextPettycashStatement(models.TransientModel):
#     _name = 'account.context.pettycash.statement'
#     _inherit = "account.context.general.ledger"
