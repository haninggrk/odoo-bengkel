# -*- coding: utf-8 -*-
import json
import urllib.request

from odoo import _, fields, models
from odoo.exceptions import UserError


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
             'when provider is Generic Webhook.',
    )
    service_reminder_days = fields.Integer(
        string='Reminder Days Before Service',
        config_parameter='fleet_sales.service_reminder_days',
        default=3,
        help='Number of days before Next Service Date when reminders are sent.',
    )
    service_reminder_provider = fields.Selection(
        selection=[
            ('webhook', 'Generic Webhook'),
            ('evolution', 'Evolution API (WhatsApp)'),
        ],
        string='Service Reminder Provider',
        config_parameter='fleet_sales.service_reminder_provider',
        default='evolution',
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
    evolution_message_template = fields.Char(
        string='Evolution Message Template',
        config_parameter='fleet_sales.evolution_message_template',
        help='Supported placeholders: {driver_name}, {next_service_date}, {vehicle_name}, '
             '{license_plate}, {service_type}, {sale_order}, {service_date}, {amount}, '
             '{currency}, {company_name}, {customer_name}, {customer_phone}, '
             '{customer_mobile}, {customer_email}, {reminder_trigger}, {reminder_sent_at}.',
    )
    evolution_test_number = fields.Char(
        string='Test WhatsApp Number',
        help='Temporary number used to send a test WhatsApp message from Settings.',
    )

    def action_test_evolution_whatsapp(self):
        self.ensure_one()

        params = self.env['ir.config_parameter'].sudo()
        base_url = params.get_param('fleet_sales.evolution_base_url')
        instance_name = params.get_param('fleet_sales.evolution_instance_name')
        api_key = params.get_param('fleet_sales.evolution_api_key')
        country_code = params.get_param('fleet_sales.evolution_country_code', '62')
        template = params.get_param('fleet_sales.evolution_message_template')

        if not (base_url and instance_name and api_key):
            raise UserError(_(
                'Evolution settings are incomplete. Please fill Base URL, Instance Name, and API Key first.'
            ))
        if not self.evolution_test_number:
            raise UserError(_('Please fill Test WhatsApp Number first.'))

        service_model = self.env['fleet.vehicle.log.services']
        normalized_number = service_model._normalize_phone(self.evolution_test_number, country_code)
        if not normalized_number:
            raise UserError(_('Invalid test phone number.'))

        payload = {
            'driver_name': 'Customer',
            'customer_name': 'Customer',
            'next_service_date': fields.Date.today(),
            'service_date': fields.Date.today(),
            'vehicle_name': 'Test Vehicle',
            'license_plate': 'B 1234 TEST',
            'service_type': 'General Service',
            'sale_order': 'SO/TEST',
            'amount': 0,
            'currency': self.env.company.currency_id.name,
            'company_name': self.env.company.name,
            'reminder_trigger': 'settings_test',
            'reminder_sent_at': str(fields.Datetime.now()),
        }
        text = service_model._build_evolution_message_text(payload, template)

        endpoint = '%s/message/sendText/%s' % (base_url.rstrip('/'), instance_name)
        body = {
            'number': normalized_number,
            'textMessage': {
                'text': text,
            },
        }
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(body).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'apikey': api_key,
            },
            method='POST',
        )

        try:
            urllib.request.urlopen(req, timeout=15)  # noqa: S310
        except Exception as exc:
            raise UserError(_('Failed to send test WhatsApp: %s') % exc)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Test WhatsApp Sent'),
                'message': _('Test message was sent to %s.') % normalized_number,
                'type': 'success',
                'sticky': False,
            },
        }
