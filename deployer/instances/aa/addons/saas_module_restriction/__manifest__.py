# -*- coding: utf-8 -*-
{
    'name': 'SaaS Module Restriction',
    'version': '18.0.1.0.0',
    'category': 'Tools',
    'summary': 'Restrict module installation based on plan allowed modules',
    'description': """
        This module restricts the installation of modules based on a whitelist
        defined in environment variable ALLOWED_MODULES.
        Only modules in the whitelist can be installed by users.
    """,
    'author': 'Odoo SaaS Platform',
    'depends': ['base'],
    'installable': True,
    'application': False,
    'auto_install': True,
    'license': 'LGPL-3',
    'data': [
        'views/ir_module_module_views.xml',
        'views/upgrade_wizard_views.xml',
        'security/ir.model.access.csv',
    ],
}
