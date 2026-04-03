# -*- coding: utf-8 -*-
from odoo import fields, models


class FleetVehicleCreateWizard(models.TransientModel):
    _name = 'fleet.vehicle.create.wizard'
    _description = 'Create Vehicle from Sales Order'

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        required=True,
        readonly=True,
    )
    license_plate = fields.Char(
        string='License Plate',
        required=True,
    )
    model_id = fields.Many2one(
        'fleet.vehicle.model',
        string='Vehicle Model',
        required=True,
    )
    odometer = fields.Float(string='Odometer')

    def action_create_vehicle(self):
        self.ensure_one()

        sale_order = self.sale_order_id
        vehicle = self.env['fleet.vehicle'].search([
            ('license_plate', '=', self.license_plate)
        ], limit=1)

        if vehicle:
            update_vals = {}
            if not vehicle.model_id:
                update_vals['model_id'] = self.model_id.id
            if sale_order.partner_id and not vehicle.driver_id:
                update_vals['driver_id'] = sale_order.partner_id.id
            if sale_order.company_id and not vehicle.company_id:
                update_vals['company_id'] = sale_order.company_id.id
            if not vehicle.sale_order_id:
                update_vals['sale_order_id'] = sale_order.id
            if update_vals:
                vehicle.write(update_vals)
        else:
            vehicle_vals = {
                'license_plate': self.license_plate,
                'model_id': self.model_id.id,
                'driver_id': sale_order.partner_id.id,
                'company_id': sale_order.company_id.id,
                'sale_order_id': sale_order.id,
            }
            vehicle = self.env['fleet.vehicle'].create(vehicle_vals)

        if self.odometer:
            vehicle.odometer = self.odometer

        sale_order.write({
            'existing_fleet_vehicle_id': vehicle.id,
            'license_plate': vehicle.license_plate,
            'fleet_vehicle_model_id': vehicle.model_id.id,
        })

        return {'type': 'ir.actions.act_window_close'}