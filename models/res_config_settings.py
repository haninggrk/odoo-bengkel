# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    commission_mode = fields.Selection(
        selection=[
            ('per_product', 'Per Product Commission'),
            ('nett_service', 'NETT Service Commission'),
            ('nett_all', 'NETT All Commission'),
            ('gross_service', 'GROSS Service Commission'),
            ('gross_all', 'GROSS All Commission'),
        ],
        string='Default Commission Mode',
        config_parameter='fleet_sales.commission_mode',
        default='per_product',
        help='Default commission mode for new Sales Orders. Can be changed per order.',
    )
    timesheet_project_id = fields.Many2one(
        'project.project',
        string='Default Timesheet Project',
        config_parameter='fleet_sales.default_timesheet_project_id',
        help='Project used when creating auto task and timesheet entries from service sale lines.',
    )
    service_reminder_webhook_url = fields.Char(
        string='Service Reminder Webhook URL',
        config_parameter='fleet_sales.service_reminder_webhook_url',
        help='A POST request with vehicle and service details will be sent to this URL '
             '3 days before each service\'s Next Service Date.',
    )
