# -*- coding: utf-8 -*-

{
    'name': 'Adapay Payment Acquirer',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 400,
    'summary': 'Payment Acquirer: Adapay Implementation',
    'version': '0.1',
    'description': """Accept ADA payments. Direct. Secure. From Anywhere. For Everyone""",
    'depends': ['payment'],
    'data': [
        'data/payment_icon.xml',
        'views/payment_views.xml',
        'views/payment_adapay_templates.xml',
        'views/assets.xml',
        'data/payment_acquirer_data.xml',
        'views/adapay_payment_update_cron.xml',
    ],
    'installable': True,
    'application': True,
    'post_init_hook': 'create_missing_journal_for_acquirers',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
