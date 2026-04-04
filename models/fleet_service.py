# -*- coding: utf-8 -*-
import json
import logging
import re
import urllib.request
from datetime import date, timedelta

from odoo import fields, models

_logger = logging.getLogger(__name__)


class FleetVehicleLogServices(models.Model):
    # Extend the fleet service model to add a back-link to the sales order
    # that triggered this service creation.
    _inherit = 'fleet.vehicle.log.services'

    # Many2one back-link: which sales order created this service record.
    # This allows navigating from the service back to the originating SO.
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        copy=False,
        readonly=True,
        help='The sales order from which this service was created.',
    )

    next_service_date = fields.Date(
        string='Next Service Date',
        help='Scheduled date for the next service. '
             'A webhook reminder will be sent 3 days in advance.',
    )

    def _build_reminder_payload(self):
        self.ensure_one()
        vehicle = self.vehicle_id
        return {
            'service_id': self.id,
            'service_name': self.name or '',
            'service_type': self.service_type_id.name if self.service_type_id else '',
            'next_service_date': str(self.next_service_date),
            'vehicle_id': vehicle.id,
            'vehicle_name': vehicle.name or '',
            'license_plate': vehicle.license_plate or '',
            'vehicle_model': vehicle.model_id.name if vehicle.model_id else '',
            'vehicle_brand': (
                vehicle.model_id.brand_id.name
                if vehicle.model_id and vehicle.model_id.brand_id else ''
            ),
            'odometer': vehicle.odometer,
            'odometer_unit': vehicle.odometer_unit or '',
            'driver_name': vehicle.driver_id.name if vehicle.driver_id else '',
            'driver_phone': vehicle.driver_id.phone if vehicle.driver_id else '',
            'driver_mobile': vehicle.driver_id.mobile if vehicle.driver_id else '',
            'driver_email': vehicle.driver_id.email if vehicle.driver_id else '',
            'sale_order': self.sale_order_id.name if self.sale_order_id else '',
        }

    def _build_evolution_message_text(self, payload, template):
        text_template = template or (
            'Hello {driver_name}, reminder for your upcoming service on {next_service_date}. '
            'Vehicle: {vehicle_name} ({license_plate}). Service: {service_type}.'
        )
        return text_template.format(
            driver_name=payload.get('driver_name') or 'Customer',
            next_service_date=payload.get('next_service_date') or '',
            vehicle_name=payload.get('vehicle_name') or '',
            license_plate=payload.get('license_plate') or '',
            service_type=payload.get('service_type') or '',
            sale_order=payload.get('sale_order') or '',
        )

    def _normalize_phone(self, number, country_code):
        digits = re.sub(r'\D', '', number or '')
        if not digits:
            return ''
        if digits.startswith('0'):
            return '%s%s' % (country_code, digits[1:])
        if digits.startswith(country_code):
            return digits
        if digits.startswith('62') or digits.startswith('1'):
            return digits
        return '%s%s' % (country_code, digits)

    def _send_webhook_reminder(self, webhook_url, payload):
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        urllib.request.urlopen(req, timeout=10)  # noqa: S310

    def _send_evolution_reminder(self, payload, base_url, instance_name, api_key, country_code, template):
        phone_raw = payload.get('driver_mobile') or payload.get('driver_phone')
        number = self._normalize_phone(phone_raw, country_code)
        if not number:
            _logger.warning(
                'Skipped Evolution reminder for service %s because no driver phone/mobile was found.',
                self.id,
            )
            return

        endpoint = '%s/message/sendText/%s' % (base_url.rstrip('/'), instance_name)
        body = {
            'number': number,
            'textMessage': {
                'text': self._build_evolution_message_text(payload, template),
            },
        }
        data = json.dumps(body).encode('utf-8')
        req = urllib.request.Request(
            endpoint,
            data=data,
            headers={
                'Content-Type': 'application/json',
                'apikey': api_key,
            },
            method='POST',
        )
        urllib.request.urlopen(req, timeout=15)  # noqa: S310

    def _cron_send_service_reminders(self):
        """Triggered by daily cron. POSTs webhook payload for every service
        whose next_service_date falls exactly 3 days from today."""
        params = self.env['ir.config_parameter'].sudo()
        provider = params.get_param('fleet_sales.service_reminder_provider', 'webhook')
        webhook_url = params.get_param('fleet_sales.service_reminder_webhook_url')
        evolution_base_url = params.get_param('fleet_sales.evolution_base_url')
        evolution_instance_name = params.get_param('fleet_sales.evolution_instance_name')
        evolution_api_key = params.get_param('fleet_sales.evolution_api_key')
        evolution_country_code = params.get_param('fleet_sales.evolution_country_code', '62')
        evolution_template = params.get_param('fleet_sales.evolution_message_template')

        if provider == 'webhook' and not webhook_url:
            return
        if provider == 'evolution' and (not evolution_base_url or not evolution_instance_name or not evolution_api_key):
            _logger.warning('Evolution reminder provider is enabled but settings are incomplete.')
            return

        target_date = date.today() + timedelta(days=3)
        services = self.search([('next_service_date', '=', target_date)])

        for service in services:
            payload = service._build_reminder_payload()
            try:
                if provider == 'evolution':
                    service._send_evolution_reminder(
                        payload,
                        evolution_base_url,
                        evolution_instance_name,
                        evolution_api_key,
                        evolution_country_code,
                        evolution_template,
                    )
                    _logger.info('Service reminder sent via Evolution: service %s', service.id)
                else:
                    service._send_webhook_reminder(webhook_url, payload)
                    _logger.info('Service reminder webhook sent: service %s', service.id)
            except Exception as exc:
                _logger.error(
                    'Failed to send service reminder for service %s via %s: %s',
                    service.id, provider, exc,
                )
