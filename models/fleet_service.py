# -*- coding: utf-8 -*-
import json
import logging
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

    def _cron_send_service_reminders(self):
        """Triggered by daily cron. POSTs webhook payload for every service
        whose next_service_date falls exactly 3 days from today."""
        webhook_url = self.env['ir.config_parameter'].sudo().get_param(
            'fleet_sales.service_reminder_webhook_url'
        )
        if not webhook_url:
            return

        target_date = date.today() + timedelta(days=3)
        services = self.search([('next_service_date', '=', target_date)])

        for service in services:
            vehicle = service.vehicle_id
            payload = {
                'service_id': service.id,
                'service_name': service.name or '',
                'service_type': service.service_type_id.name if service.service_type_id else '',
                'next_service_date': str(service.next_service_date),
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
                'sale_order': service.sale_order_id.name if service.sale_order_id else '',
            }
            try:
                data = json.dumps(payload).encode('utf-8')
                req = urllib.request.Request(
                    webhook_url,
                    data=data,
                    headers={'Content-Type': 'application/json'},
                    method='POST',
                )
                urllib.request.urlopen(req, timeout=10)  # noqa: S310
                _logger.info(
                    'Service reminder webhook sent: service %s, vehicle %s',
                    service.id, vehicle.license_plate,
                )
            except Exception as exc:
                _logger.error(
                    'Failed to send service reminder webhook for service %s: %s',
                    service.id, exc,
                )
