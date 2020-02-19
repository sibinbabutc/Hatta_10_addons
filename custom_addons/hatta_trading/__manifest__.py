{
    'name': 'Hatta Trading',
    'version': '0.1',
    'summary': 'Hatta Trading',
    'description': 'Hatta Trading',
    'author': 'FourmalTech',
    'website': 'www.fourmaltech.com',
    'depends': ['sale', 'purchase', 'account', 'stock', 'crm', 'account_petty_cash_ft', 'report_docx'],
    'data': [
        'data/user_groups.xml',
        'data/purchase_mail_template_data.xml',
        'security/hatta_security.xml',
        'security/ir.model.access.csv',
        'reports/hatta_external_layout.xml',
        'reports/sale_quotation.xml',
        'reports/delivery_slip.xml',
        'reports/qual_just_report.xml',
        'reports/remarks_report.xml',
        'data/hatta_data.xml',
        'data/mail_template_data.xml',
        'wizards/wizard_supplier_bid_view.xml',
        'wizards/order_revisions_view.xml',
        'wizards/covering_letter.xml',
        'wizards/stock_product_view.xml',
        'wizards/wizard_create_rfq_view.xml',
        'wizards/wizard_po_confirmation_view.xml',
        'wizards/wizard_rfq_selection_view.xml',
        'wizards/wizard_zero_unit_price_view.xml',
        'wizards/wizard_percentage_distribution_mapping.xml',
        # 'wizards/purchase_report_view.xml',
        'views/templates.xml',
        'views/hatta_product_view.xml',
        'views/enquiry_details_view.xml',
        'views/account_invoice_view.xml',
        'views/crm_lead_view.xml',
        'views/cost_sheet_view.xml',
        'reports/cost_sheet_report.xml',
        'views/product_landed_cost_view.xml',
        'views/hatta_purchase_view.xml',
        'views/hatta_sale_view.xml',
        'views/hatta_partner_view.xml',
        'views/cost_center_view.xml',
        'views/hatta_menu.xml',
        'views/analytic_account_view.xml',
        'views/quotation_status_view.xml',
        'views/shipping_invoice_view.xml',
        'views/manufacturer_view.xml',
        'views/res_config_view.xml',
        'views/stock_picking_inherited.xml',
        'reports/request_for_quotation.xml',
        'reports/draft_purchase_order.xml',
        'reports/consolidated_worksheet.xml',
        'reports/worksheet_report.xml',
        'reports/covering_letter_report.xml',
        'reports/po_datasheet.xml',
        'reports/sale_order.xml',
        # 'reports/qualification_justification.xml',
        'reports/delivery_note.xml',
        'reports/commercial_format_report.xml',
        # 'reports/cost_sheet_component_report.xml',
        'reports/report_invoice_template.xml',
    ],
    'qweb': [
            "static/src/xml/*.xml",
            ],
    'installable': True,
    'auto_install': False,
}