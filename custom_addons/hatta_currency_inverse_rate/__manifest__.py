{
    'name': 'Hatta Currency Inverse Rate',
    'version': '1.0',
    'summary': 'Hatta Currency Inverse Rate',
    'category': 'Currency',
    'author': 'Fourmaltech Solutions',
    'description': '''
Currency Inverse Rate
==========================
In some countries where currency rate is big enough compared to USD or EUR, 
we are used to see exchange rate in the inverse way as Odoo shows it. 

The module shows rate FROM base currency and not TO base currency. For eg.

* Base Currency IDR: 1.0
* USD rate: 12,000 (in Odoo way: 1 / 12,000 = 0.000083333333333)

Using this module, we enter the 12,000 and not the 0.000083333333333.

This module also add number of decimal precision on the currency rate
to avoid rounding for those currencies.


    ''',
    'depends': [
        'base',
    ],
    'data': [
        'views/res_currency_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
