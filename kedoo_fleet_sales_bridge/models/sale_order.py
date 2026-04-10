# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    license_plate = fields.Char(
        string='License Plate',
        copy=False,
        help='Vehicle license plate number. When the order is confirmed, a fleet service is created.',
    )
    service_date = fields.Date(
        string='Service Date',
        copy=True,
        help='Date of the fleet service. Defaults to today when the service is created.',
    )
    service_type_id = fields.Many2one(
        'fleet.service.type',
        string='Service Type',
        copy=True,
        help='Type of fleet service to create when confirming this order.',
    )
    fleet_vehicle_model_id = fields.Many2one(
        'fleet.vehicle.model',
        string='Vehicle Model',
        copy=True,
        help='Vehicle model used when a new fleet vehicle is created.',
    )
    existing_fleet_vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Vehicle',
        copy=False,
        help='Select an existing vehicle for this customer or create a new one.',
    )
    has_existing_vehicles = fields.Boolean(
        string='Has Existing Vehicles',
        compute='_compute_has_existing_vehicles',
    )
    fleet_vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Fleet Vehicle',
        copy=False,
        readonly=True,
        help='Fleet vehicle linked to this sales order.',
    )
    fleet_service_id = fields.Many2one(
        'fleet.vehicle.log.services',
        string='Fleet Service',
        copy=False,
        readonly=True,
        help='Fleet service created from this sales order.',
    )
    fleet_vehicle_count = fields.Integer(
        string='Fleet Vehicle Count',
        compute='_compute_fleet_vehicle_count',
    )
    fleet_service_count = fields.Integer(
        string='Fleet Service Count',
        compute='_compute_fleet_service_count',
    )

    @api.depends('partner_id')
    def _compute_has_existing_vehicles(self):
        for order in self:
            if order.partner_id:
                count = self.env['fleet.vehicle'].search_count([
                    ('driver_id', '=', order.partner_id.id)
                ])
                order.has_existing_vehicles = count > 0
            else:
                order.has_existing_vehicles = False

    @api.depends('fleet_vehicle_id')
    def _compute_fleet_vehicle_count(self):
        for order in self:
            order.fleet_vehicle_count = 1 if order.fleet_vehicle_id else 0

    @api.depends('fleet_service_id')
    def _compute_fleet_service_count(self):
        for order in self:
            order.fleet_service_count = 1 if order.fleet_service_id else 0

    @api.onchange('existing_fleet_vehicle_id')
    def _onchange_existing_fleet_vehicle_id(self):
        if self.existing_fleet_vehicle_id:
            self.license_plate = self.existing_fleet_vehicle_id.license_plate
            self.fleet_vehicle_model_id = self.existing_fleet_vehicle_id.model_id

    @api.onchange('partner_id')
    def _onchange_partner_id_fleet(self):
        self.existing_fleet_vehicle_id = False

    def action_confirm(self):
        result = super().action_confirm()
        for order in self:
            if order.license_plate and not order.fleet_service_id:
                order._create_fleet_service()
        return result

    def _create_fleet_service(self):
        self.ensure_one()
        vehicle = self._find_or_create_fleet_vehicle()

        service_type = self.service_type_id
        if not service_type:
            service_type = self.env['fleet.service.type'].search([
                ('name', '=', 'Dedicated')
            ], limit=1)
        if not service_type:
            service_type = self.env['fleet.service.type'].search([], limit=1)

        service_vals = {
            'vehicle_id': vehicle.id,
            'sale_order_id': self.id,
            'description': _('Service from Sales Order %s') % self.name,
            'date': self.service_date or fields.Date.today(),
            'amount': self.amount_total,
            'company_id': self.company_id.id,
            'service_type_id': service_type.id if service_type else False,
        }
        service = self.env['fleet.vehicle.log.services'].create(service_vals)
        self.fleet_service_id = service.id
        self.fleet_vehicle_id = vehicle.id

        self.message_post(
            body=_('Fleet service created for vehicle %s from this sales order.') % vehicle.name
        )
        return service

    def _find_or_create_fleet_vehicle(self):
        self.ensure_one()

        if self.existing_fleet_vehicle_id:
            vehicle = self.existing_fleet_vehicle_id
            update_vals = {}
            if not vehicle.sale_order_id:
                update_vals['sale_order_id'] = self.id
            if self.partner_id and not vehicle.driver_id:
                update_vals['driver_id'] = self.partner_id.id
            if self.company_id and not vehicle.company_id:
                update_vals['company_id'] = self.company_id.id
            if self.fleet_vehicle_model_id and not vehicle.model_id:
                update_vals['model_id'] = self.fleet_vehicle_model_id.id
            if update_vals:
                vehicle.write(update_vals)
            return vehicle

        existing = self.env['fleet.vehicle'].search([
            ('license_plate', '=', self.license_plate)
        ], limit=1)
        if existing:
            return existing

        vehicle_vals = {
            'license_plate': self.license_plate,
            'sale_order_id': self.id,
            'driver_id': self.partner_id.id if self.partner_id else False,
            'company_id': self.company_id.id if self.company_id else False,
        }
        if self.fleet_vehicle_model_id:
            vehicle_vals['model_id'] = self.fleet_vehicle_model_id.id
        else:
            default_model = self.env['fleet.vehicle.model'].search([], limit=1)
            if default_model:
                vehicle_vals['model_id'] = default_model.id

        return self.env['fleet.vehicle'].create(vehicle_vals)

    def action_view_fleet_vehicle(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('fleet.fleet_vehicle_action')
        action['views'] = [(False, 'form')]
        action['res_id'] = self.fleet_vehicle_id.id
        action['context'] = {'create': False}
        return action

    def action_open_selected_vehicle_page(self):
        self.ensure_one()
        if not self.existing_fleet_vehicle_id:
            return False

        return {
            'type': 'ir.actions.act_url',
            'url': '%s/odoo/sales/%s/fleet/%s' % (
                self.get_base_url(),
                self.id,
                self.existing_fleet_vehicle_id.id,
            ),
            'target': 'self',
        }

    def action_view_fleet_service(self):
        self.ensure_one()
        if self.fleet_service_id and self.fleet_vehicle_id:
            return {
                'type': 'ir.actions.act_url',
                'url': '%s/odoo/sales/%s/fleet/%s/%s/action-643/%s' % (
                    self.get_base_url(),
                    self.id,
                    self.fleet_vehicle_id.id,
                    self.id,
                    self.fleet_service_id.id,
                ),
                'target': 'self',
            }

        action = self.env['ir.actions.act_window']._for_xml_id('fleet.fleet_vehicle_log_services_action')
        action['views'] = [(False, 'form')]
        action['res_id'] = self.fleet_service_id.id
        action['context'] = {'create': False}
        return action
