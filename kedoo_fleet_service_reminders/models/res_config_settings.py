# -*- coding: utf-8 -*-
import json
import urllib.request

from odoo import _, fields, models
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    service_reminder_webhook_url = fields.Char(
        string='Service Reminder Webhook URL',
        config_parameter='kedoo_fleet_service_reminders.webhook_url',
        help='POST request with vehicle and service details is sent to this URL when provider is Generic Webhook.',
    )
    service_reminder_days = fields.Integer(
        string='Reminder Days Before Service',
        config_parameter='kedoo_fleet_service_reminders.days_before',
        default=3,
        help='Number of days before Next Service Date when reminders are sent.',
    )
    service_reminder_provider = fields.Selection(
        selection=[
            ('webhook', 'Generic Webhook'),
            ('evolution', 'Evolution API (WhatsApp)'),
        ],
        string='Service Reminder Provider',
        config_parameter='kedoo_fleet_service_reminders.provider',
        default='evolution',
        help='Choose where automatic service reminders are sent.',
    )
    evolution_base_url = fields.Char(
        string='Evolution Base URL',
        config_parameter='kedoo_fleet_service_reminders.evolution_base_url',
        help='Example: https://evolution.cashfloo.com',
    )
    evolution_instance_name = fields.Char(
        string='Evolution Instance Name',
        config_parameter='kedoo_fleet_service_reminders.evolution_instance_name',
        help='Instance name used in endpoint /message/sendText/<instance>.',
    )
    evolution_api_key = fields.Char(
        string='Evolution API Key',
        config_parameter='kedoo_fleet_service_reminders.evolution_api_key',
        help='API key sent in the apikey header.',
    )
    evolution_country_code = fields.Char(
        string='Default Country Code',
        config_parameter='kedoo_fleet_service_reminders.evolution_country_code',
        default='62',
        help='Used to normalize numbers that start with 0.',
    )
    evolution_message_template = fields.Char(
        string='Evolution Message Template',
        config_parameter='kedoo_fleet_service_reminders.evolution_message_template',
        help='Supported placeholders include customer, vehicle, service, and schedule context keys.',
    )
    evolution_test_number = fields.Char(
        string='Test WhatsApp Number',
        help='Temporary number used to send a test WhatsApp message from Settings.',
    )

    def action_test_evolution_whatsapp(self):
        self.ensure_one()

        params = self.env['ir.config_parameter'].sudo()
        base_url = params.get_param('kedoo_fleet_service_reminders.evolution_base_url')
        instance_name = params.get_param('kedoo_fleet_service_reminders.evolution_instance_name')
        api_key = params.get_param('kedoo_fleet_service_reminders.evolution_api_key')
        country_code = params.get_param('kedoo_fleet_service_reminders.evolution_country_code', '62')
        template = params.get_param('kedoo_fleet_service_reminders.evolution_message_template')

        if not (base_url and instance_name and api_key):
            raise UserError(_(
                'Evolution settings are incomplete. Fill Base URL, Instance Name, and API Key first.'
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
            'text': text,
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
