{
    'name': 'Lead Export Guard',
    'version': '19.0.1.0.0',
    'summary': 'Blocks lead export for everyone; only users granted access can export. Logs every attempt.',
    'author': 'Otomater',
    'website': 'https://otomater.com',
    'license': 'OPL-1',
    'category': 'Sales/CRM',
    'depends': ['base', 'web', 'custom_leads_19'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/export_guard_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
    'application': False,
}
