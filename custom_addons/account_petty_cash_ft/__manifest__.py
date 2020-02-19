




{
    "name": "Petty Cash",
    "summary": "Automated management of petty cash funds",
    "description": """
    """,
    "author": "FourmalTech Solutions",
    "website": "http://www.fourmaltech.com/",
    "license": "AGPL-3",
    "version": "8.0.1.0",
    "category": "Accounting & Finance",
    "depends": [
        'account_asset',
        'account_accountant',
        'project',
        'account_cheque_ft',
        'hr',
        'account_voucher_ft'
    ],
    "data": [
        'security/petty_cash.xml',
        'security/ir.model.access.csv',
        'data/petty_cash_data.xml',
        'views/pettycash_statement_view.xml',
        'views/petty_cash_voucher_view.xml',
        'reports/report_petty_cash_wizard_view.xml',
        'views/petty_cash_view.xml',
        'views/account_payment_view.xml',
        'reports/petty_cash_voucher_report.xml',
        'reports/petty_cash_statement_report.xml',
        'reports/petty_cash_reports.xml',
        'reports/petty_cash_statement.xml',
        'reports/petty_cash_payment_voucher_report.xml',
        'data/log_data_for_voucher.xml'
    ],
    "installable": True,
    "active": True,
}



