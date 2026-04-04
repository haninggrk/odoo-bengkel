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
    service_reminder_provider = fields.Selection(
        selection=[
            ('webhook', 'Generic Webhook'),
            ('evolution', 'Evolution API (WhatsApp)'),
        ],
        string='Service Reminder Provider',
        config_parameter='fleet_sales.service_reminder_provider',
        default='webhook',
        help='Choose where automatic service reminders are sent.',
    )
    evolution_base_url = fields.Char(
        string='Evolution Base URL',
        config_parameter='fleet_sales.evolution_base_url',
        help='Example: https://evolution.cashfloo.com',
    )
    evolution_instance_name = fields.Char(
        string='Evolution Instance Name',
        config_parameter='fleet_sales.evolution_instance_name',
        help='Instance name used in Evolution endpoint /message/sendText/<instance>.',
    )
    evolution_api_key = fields.Char(
        string='Evolution API Key',
        config_parameter='fleet_sales.evolution_api_key',
        help='API key sent in the apikey header.',
    )
    evolution_country_code = fields.Char(
        string='Default Country Code',
        config_parameter='fleet_sales.evolution_country_code',
        default='62',
        help='Used to normalize numbers that start with 0.',
    )
    evolution_message_template = fields.Text(
        string='Evolution Message Template',
        config_parameter='fleet_sales.evolution_message_template',
        help='Supported placeholders: {driver_name}, {next_service_date}, {vehicle_name}, '
             '{license_plate}, {service_type}, {sale_order}.',
    )
