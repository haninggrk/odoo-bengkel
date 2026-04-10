# -*- coding: utf-8 -*-
{
    'name': 'Kedoo Sales Timesheet Assignment',
    'version': '19.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Assign service lines, auto-generate tasks, and track timesheets',
    'author': 'Kedoo',
    'license': 'LGPL-3',
    'depends': [
        'kedoo_sales_commission',
        'project',
        'hr_timesheet',
    ],
    'data': [
        'views/project_views.xml',
        'views/sale_order_views.xml',
        'views/timesheet_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'post_init_hook': 'post_init_hook',
}
