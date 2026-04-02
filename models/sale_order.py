# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class SaleOrder(models.Model):
    # Extending the existing 'sale.order' model to add fleet-related fields and behavior.
    # When a sales order is confirmed, it automatically creates a fleet service
    # (and a fleet vehicle if one doesn't already exist for the given license plate).
    _inherit = 'sale.order'

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------

    # Char field for storing the vehicle's license plate on the sales order.
    # copy=False ensures that when the user duplicates a quotation,
    # the license plate is NOT copied (each service order is unique).
    license_plate = fields.Char(
        string='License Plate',
        copy=False,
        help='Vehicle license plate number. When the order is confirmed, '
             'a fleet service will be created automatically.'
    )

    # Many2one to 'fleet.vehicle.model' lets the user pick a vehicle brand/model
    # (e.g., Toyota Avanza, Honda Civic) from the fleet module's catalog.
    # copy=True means this value IS copied when duplicating the quotation,
    # because a customer may order the same vehicle model again.
    fleet_vehicle_model_id = fields.Many2one(
        'fleet.vehicle.model',
        string='Vehicle Model',
        copy=True,
        help='Select the vehicle brand/model for the fleet vehicle to be created.'
    )

    # Lets the user pick from the customer's EXISTING vehicles.
    # The domain filters by partner_id so only the current customer's vehicles appear.
    # When selected, an @api.onchange auto-fills license_plate and vehicle model.
    existing_fleet_vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Existing Vehicle',
        copy=False,
        help='Select a vehicle from the customer\'s history. '
             'This will auto-fill the license plate and vehicle model.',
    )

    # Computed boolean: True if the selected customer has at least one vehicle
    # in the fleet. Used in the view to show/hide the 'Existing Vehicle' field.
    has_existing_vehicles = fields.Boolean(
        string='Has Existing Vehicles',
        compute='_compute_has_existing_vehicles',
    )

    # Many2one to the actual 'fleet.vehicle' record (existing or newly created).
    # readonly=True because this is set programmatically, not by the user.
    fleet_vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Fleet Vehicle',
        copy=False,
        readonly=True,
        help='The fleet vehicle linked to this sales order.'
    )

    # Many2one to the fleet service record created on SO confirmation.
    # This is the primary link — the SO creates a service, not just a vehicle.
    fleet_service_id = fields.Many2one(
        'fleet.vehicle.log.services',
        string='Fleet Service',
        copy=False,
        readonly=True,
        help='The fleet service created from this sales order.'
    )

    # Computed field: returns 1 if a vehicle exists, 0 otherwise.
    # Used by the smart button in the view to show/hide the vehicle count badge.
    fleet_vehicle_count = fields.Integer(
        string='Fleet Vehicle Count',
        compute='_compute_fleet_vehicle_count',
    )

    # Computed field: returns 1 if a service exists, 0 otherwise.
    # Used by the service smart button in the view.
    fleet_service_count = fields.Integer(
        string='Fleet Service Count',
        compute='_compute_fleet_service_count',
    )

    # -------------------------------------------------------------------------
    # COMPUTED METHODS
    # -------------------------------------------------------------------------

    @api.depends('partner_id')
    def _compute_has_existing_vehicles(self):
        """Check if the selected customer has any fleet vehicles (as driver).
        
        This is recomputed whenever partner_id changes. The result controls
        visibility of the 'Existing Vehicle' dropdown in the form view.
        """
        for order in self:
            if order.partner_id:
                # search_count is more efficient than search() when you only
                # need to know if records exist — it returns an integer.
                count = self.env['fleet.vehicle'].search_count([
                    ('driver_id', '=', order.partner_id.id)
                ])
                order.has_existing_vehicles = count > 0
            else:
                order.has_existing_vehicles = False

    # @api.depends('fleet_vehicle_id') tells Odoo to recompute this field
    # whenever 'fleet_vehicle_id' changes. This ensures the count is always up-to-date.
    @api.depends('fleet_vehicle_id')
    def _compute_fleet_vehicle_count(self):
        for order in self:
            order.fleet_vehicle_count = 1 if order.fleet_vehicle_id else 0

    @api.depends('fleet_service_id')
    def _compute_fleet_service_count(self):
        for order in self:
            order.fleet_service_count = 1 if order.fleet_service_id else 0

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange('existing_fleet_vehicle_id')
    def _onchange_existing_fleet_vehicle_id(self):
        """Auto-fill license plate and vehicle model when an existing vehicle is selected.
        
        @api.onchange is triggered in the UI when the user changes the field value.
        It runs client-side (before saving) to give instant feedback.
        """
        if self.existing_fleet_vehicle_id:
            self.license_plate = self.existing_fleet_vehicle_id.license_plate
            self.fleet_vehicle_model_id = self.existing_fleet_vehicle_id.model_id

    @api.onchange('partner_id')
    def _onchange_partner_id_fleet(self):
        """Clear existing vehicle selection when the customer changes.
        
        If the user switches to a different customer, the previously selected
        vehicle may not belong to the new customer, so we reset it.
        """
        self.existing_fleet_vehicle_id = False

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------

    def action_confirm(self):
        """Override to create fleet vehicle + service when order is confirmed.
        
        super().action_confirm() calls the ORIGINAL action_confirm() from the
        'sale' module. This is the standard pattern to extend behavior:
        1. Call super() to preserve existing logic (e.g., stock moves, invoicing)
        2. Add your custom logic after
        """
        result = super().action_confirm()

        for order in self:
            # Only create a service if:
            # 1. A license plate was provided (the user wants fleet integration)
            # 2. No service has been created yet (avoid duplicates on re-confirmation)
            if order.license_plate and not order.fleet_service_id:
                order._create_fleet_service()

        return result

    # -------------------------------------------------------------------------
    # PRIVATE METHODS
    # -------------------------------------------------------------------------

    def _create_fleet_service(self):
        """Create a fleet service (and vehicle if needed) from the sales order.
        
        Flow:
        1. Find or create the fleet vehicle by license plate
        2. Create a fleet service record linked to that vehicle
        3. Link both the vehicle and service back to this SO
        """
        self.ensure_one()

        # Step 1: Find or create the fleet vehicle
        vehicle = self._find_or_create_fleet_vehicle()

        # Step 2: Create the fleet service linked to the vehicle and this SO
        service_vals = {
            'vehicle_id': vehicle.id,
            'sale_order_id': self.id,
            'description': _('Service from Sales Order %s') % self.name,
            'date': fields.Date.today(),
            'company_id': self.company_id.id,
        }
        service = self.env['fleet.vehicle.log.services'].create(service_vals)

        # Step 3: Link both records back to this sales order
        self.fleet_service_id = service.id
        self.fleet_vehicle_id = vehicle.id

        # Post a chatter message so users can see in the activity log
        # that a service and vehicle were created/linked.
        self.message_post(
            body=_('Fleet service created for vehicle %s from this sales order.') % vehicle.name
        )

        return service

    def _find_or_create_fleet_vehicle(self):
        """Find an existing vehicle by license plate, or create a new one.
        
        If the user selected an existing vehicle via the dropdown, use that.
        Otherwise, search by license plate. If no vehicle is found, create one.
        This prevents duplicate vehicles for the same license plate.
        """
        self.ensure_one()

        # If the user selected an existing vehicle, use it directly
        if self.existing_fleet_vehicle_id:
            return self.existing_fleet_vehicle_id

        # Search for an existing vehicle with this license plate
        existing = self.env['fleet.vehicle'].search([
            ('license_plate', '=', self.license_plate)
        ], limit=1)
        if existing:
            return existing

        # No existing vehicle found — create a new one
        vehicle_vals = {
            'license_plate': self.license_plate,
            'sale_order_id': self.id,
            'driver_id': self.partner_id.id,
            'company_id': self.company_id.id,
        }

        # Use the vehicle model selected by the user, or fall back to the first
        # available model. 'model_id' is a required field on fleet.vehicle.
        if self.fleet_vehicle_model_id:
            vehicle_vals['model_id'] = self.fleet_vehicle_model_id.id
        else:
            default_model = self.env['fleet.vehicle.model'].search([], limit=1)
            if default_model:
                vehicle_vals['model_id'] = default_model.id

        return self.env['fleet.vehicle'].create(vehicle_vals)

    # -------------------------------------------------------------------------
    # SMART BUTTON ACTIONS
    # -------------------------------------------------------------------------

    def action_view_fleet_vehicle(self):
        """Open the fleet vehicle form view.
        
        Called when the user clicks the 'Vehicle' smart button on the SO form.
        Returns an action dictionary that navigates to the linked vehicle.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Fleet Vehicle'),
            'res_model': 'fleet.vehicle',
            'view_mode': 'form',
            'res_id': self.fleet_vehicle_id.id,
            'context': {'create': False},
        }

    def action_view_fleet_service(self):
        """Open the fleet service form view.
        
        Called when the user clicks the 'Service' smart button on the SO form.
        Returns an action dictionary that navigates to the linked service.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Fleet Service'),
            'res_model': 'fleet.vehicle.log.services',
            'view_mode': 'form',
            'res_id': self.fleet_service_id.id,
            'context': {'create': False},
        }
