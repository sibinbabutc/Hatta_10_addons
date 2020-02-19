# -*- coding: utf-8 -*-
{
    'name': "Receipt & Payment Voucher",

    'summary': """
        Customize Payment for Vouchers""",

    'description': """
        This module enhances the Payment as Receipt Voucher and Payment Voucher
    """,

    'author': "Fourmaltech Solutions",
    'website': "http://www.fourmaltech.com",

    'category': 'Accounting',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['account', 'account_cheque_ft'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/account_voucher_data.xml',
        'views/account_payment_view.xml',
        'views/templates.xml',
        'reports/account_voucher_report_layout.xml',
        'reports/account_voucher_reports.xml',
        'reports/reports.xml',
        'reports/account_voucher_new_format.xml',
        # 'views/account_move_view.xml',
        'reports/account_internal_transfer_voucher_report.xml',
        'reports/pv_with_cheque_report.xml',
        'data/mail_template_for_pv_with_cheque.xml',
        'data/log_data_for_voucher.xml',
        'data/account_payment_method_data.xml',

    ],
}