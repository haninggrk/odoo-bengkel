# -*- coding: utf-8 -*-
{
    'name': 'Kedoo Fleet Service Reminders',
    'version': '19.0.1.0.0',
    'category': 'Fleet',
    'summary': 'Automated service reminders via webhook or Evolution API',
    'author': 'Kedoo',
    'license': 'LGPL-3',
    'depends': [
        'fleet',
    ],
    'data': [
        'data/fleet_service_cron.xml',
        'views/fleet_vehicle_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
}
