# -*- coding: utf-8 -*-
from collections import defaultdict
import json
import logging
import re
import urllib.request
from urllib.error import HTTPError
from datetime import date, timedelta

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import format_date

_logger = logging.getLogger(__name__)

DEFAULT_EVOLUTION_TEMPLATE = (
    'Halo Bapak/Ibu [Nama] 👋\n\n'
    'Kami dari [Nama Bengkel] ingin mengingatkan jadwal servis kendaraan Anda:\n\n'
    '1️⃣ Kendaraan: [Merk Mobil] ([No. Polisi])\n'
    '2️⃣ Servis terakhir: [Tanggal Servis Terakhir]\n'
    '3️⃣ Servis berikutnya: [Tanggal Servis Berikutnya]\n\n'
    '✅ Agar kendaraan tetap prima, kami sarankan booking servis sekarang.\n'
    '📞 Silakan hubungi kami untuk penjadwalan.\n\n'
    'Terima kasih 🙏'
)


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
             'A reminder will be sent in advance based on settings.',
    )
    reminder_sent = fields.Boolean(
        string='Reminder Sent',
        default=False,
        copy=False,
        help='Checked automatically after reminder is sent successfully.',
    )
    reminder_sent_at = fields.Datetime(
        string='Reminder Sent At',
        copy=False,
    )
    reminder_last_trigger = fields.Selection(
        selection=[
            ('cron', 'Cron'),
            ('manual', 'Manual'),
        ],
        string='Last Reminder Trigger',
        copy=False,
    )

    def _build_reminder_payload(self):
        self.ensure_one()
        vehicle = self.vehicle_id
        driver = vehicle.driver_id
        partner = driver.commercial_partner_id if driver else False
        service_date = self.date.date() if hasattr(self.date, 'date') else self.date
        service_date = fields.Date.to_date(service_date) if service_date else False
        next_service_date = fields.Date.to_date(self.next_service_date) if self.next_service_date else False
        lang_code = self.env.user.lang or 'id_ID'
        service_label = (
            getattr(self, 'name', False)
            or self.display_name
            or (self.service_type_id.name if self.service_type_id else False)
            or 'Service %s' % self.id
        )
        driver_phone = getattr(driver, 'phone', '') if driver else ''
        driver_mobile = getattr(driver, 'mobile', False) if driver else False
        driver_mobile = driver_mobile or driver_phone
        driver_email = getattr(driver, 'email', '') if driver else ''
        return {
            'service_id': self.id,
            'service_name': service_label,
            'service_type': self.service_type_id.name if self.service_type_id else '',
            'service_date': str(service_date or ''),
            'next_service_date': str(self.next_service_date),
            'service_date_formatted': (
                format_date(self.env, service_date, lang_code=lang_code) if service_date else ''
            ),
            'next_service_date_formatted': (
                format_date(self.env, next_service_date, lang_code=lang_code) if next_service_date else ''
            ),
            'amount': self.amount,
            'currency': self.currency_id.name if self.currency_id else '',
            'company_name': self.company_id.name if self.company_id else '',
            'vehicle_id': vehicle.id,
            'vehicle_name': vehicle.name or '',
            'license_plate': vehicle.license_plate or '',
            'vehicle_model': vehicle.model_id.name if vehicle.model_id else '',
            'vehicle_brand': (
                vehicle.model_id.brand_id.name
                if vehicle.model_id and vehicle.model_id.brand_id else ''
            ),
            'service_description': self.description or '',
            'odometer': vehicle.odometer,
            'odometer_unit': vehicle.odometer_unit or '',
            'driver_name': driver.name if driver else '',
            'driver_phone': driver_phone,
            'driver_mobile': driver_mobile,
            'driver_email': driver_email,
            'customer_name': driver.name if driver else '',
            'customer_phone': driver_phone,
            'customer_mobile': driver_mobile,
            'customer_email': driver_email,
            'customer_company': partner.name if partner else '',
            'sale_order': self.sale_order_id.name if self.sale_order_id else '',
        }

    def _build_evolution_message_text(self, payload, template):
        text_template = template or DEFAULT_EVOLUTION_TEMPLATE

        # Support user-friendly bracket placeholders in saved templates.
        bracket_placeholders = {
            '[Nama]': '{customer_name}',
            '[Nama Bengkel]': '{company_name}',
            '[Merk Mobil]': '{vehicle_brand} {vehicle_model}',
            '[No. Polisi]': '{license_plate}',
            '[Tanggal Servis Terakhir]': '{service_date_formatted}',
            '[Tanggal Servis Berikutnya]': '{next_service_date_formatted}',
        }
        for token, replacement in bracket_placeholders.items():
            text_template = text_template.replace(token, replacement)

        values = defaultdict(str, payload)
        values['driver_name'] = payload.get('driver_name') or payload.get('customer_name') or 'Customer'
        values['customer_name'] = payload.get('customer_name') or payload.get('driver_name') or 'Customer'

        try:
            return text_template.format_map(values)
        except ValueError as exc:
            raise UserError(_('Invalid message template format: %s') % exc)

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
            'text': self._build_evolution_message_text(payload, template),
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
        try:
            urllib.request.urlopen(req, timeout=15)  # noqa: S310
        except HTTPError as exc:
            body = ''
            try:
                body = exc.read().decode('utf-8', errors='replace')
            except Exception:  # noqa: BLE001
                body = ''
            details = body or str(exc)
            raise UserError(_('Evolution API request failed (%s): %s') % (exc.code, details))

    def _send_service_reminder(self, trigger='cron', raise_on_error=False):
        self.ensure_one()

        params = self.env['ir.config_parameter'].sudo()
        provider = params.get_param('fleet_sales.service_reminder_provider', 'webhook')
        webhook_url = params.get_param('fleet_sales.service_reminder_webhook_url')
        evolution_base_url = params.get_param('fleet_sales.evolution_base_url')
        evolution_instance_name = params.get_param('fleet_sales.evolution_instance_name')
        evolution_api_key = params.get_param('fleet_sales.evolution_api_key')
        evolution_country_code = params.get_param('fleet_sales.evolution_country_code', '62')
        evolution_template = params.get_param('fleet_sales.evolution_message_template')

        if provider == 'webhook' and not webhook_url:
            if evolution_base_url and evolution_instance_name and evolution_api_key:
                provider = 'evolution'
            else:
                msg = _(
                    'Service Reminder Provider is set to Generic Webhook, but Webhook URL is empty. '
                    'If you want WhatsApp from this module, switch provider to Evolution API and fill '
                    'Evolution Base URL, Instance Name, and API Key.'
                )
                if raise_on_error:
                    raise UserError(msg)
                _logger.warning(msg)
                return False

        if provider == 'evolution' and (not evolution_base_url or not evolution_instance_name or not evolution_api_key):
            msg = _('Evolution reminder provider is enabled but settings are incomplete.')
            if raise_on_error:
                raise UserError(msg)
            _logger.warning(msg)
            return False

        payload = self._build_reminder_payload()
        payload['reminder_trigger'] = trigger
        payload['reminder_sent_at'] = str(fields.Datetime.now())

        try:
            if provider == 'evolution':
                self._send_evolution_reminder(
                    payload,
                    evolution_base_url,
                    evolution_instance_name,
                    evolution_api_key,
                    evolution_country_code,
                    evolution_template,
                )
                _logger.info('Service reminder sent via Evolution: service %s', self.id)
            else:
                self._send_webhook_reminder(webhook_url, payload)
                _logger.info('Service reminder webhook sent: service %s', self.id)

            self.write({
                'reminder_sent': True,
                'reminder_sent_at': fields.Datetime.now(),
                'reminder_last_trigger': trigger,
            })
        except UserError:
            if raise_on_error:
                raise
            _logger.error(
                'Failed to send service reminder for service %s via %s with user error.',
                self.id, provider,
            )
            return False
        except Exception as exc:
            if raise_on_error:
                raise UserError(_('Failed to send reminder: %s') % exc)
            _logger.error(
                'Failed to send service reminder for service %s via %s: %s',
                self.id, provider, exc,
            )
            return False

        return True

    def action_send_service_reminder_now(self):
        for service in self:
            if service.reminder_sent:
                sent_at = service.reminder_sent_at or '-'
                raise UserError(_('Reminder already sent for this service at %s.') % sent_at)
            service._send_service_reminder(trigger='manual', raise_on_error=True)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Reminder Sent'),
                'message': _('Service reminder has been sent.'),
                'type': 'success',
                'sticky': False,
            },
        }

    def _cron_send_service_reminders(self):
        """Triggered by daily cron. Sends reminders for upcoming services
        from today until N days ahead, once per service record."""
        params = self.env['ir.config_parameter'].sudo()
        reminder_days = int(params.get_param('fleet_sales.service_reminder_days', 3) or 3)
        today = date.today()
        target_date = today + timedelta(days=reminder_days)
        services = self.search([
            ('next_service_date', '>=', today),
            ('next_service_date', '<=', target_date),
            ('reminder_sent', '=', False),
        ])

        for service in services:
            service._send_service_reminder(trigger='cron', raise_on_error=False)
