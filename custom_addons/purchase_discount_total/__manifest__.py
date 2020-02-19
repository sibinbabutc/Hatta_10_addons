{
    'name': 'Purchase Discount',
    'description': 'Apply discount on purchase invoice total',
    'version': '1.0.0',
    'license': 'LGPL-3',
    'author': 'FourmalTech',
    'website': '',
    'depends': ['hatta_trading','purchase', 'account',],
    'data': [
        'views/purchase_order_view.xml',
        'views/account_invoice_view.xml',
    ],
    'application': True,
    'installable': True,
}