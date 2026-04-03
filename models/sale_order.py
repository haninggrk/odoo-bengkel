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
    
    service_date = fields.Date(
        string='Service Date',
        copy=True,
        help='Date of the fleet service. Defaults to today\'s date when the service is created.'
    )
    
    

    # Many2one to 'fleet.service.type' lets the user pick the type of service
    # (e.g., "Dedicated", "Oil Change", "Periodic Maintenance").
    # The correct model name is 'fleet.service.type' (NOT 'fleet.vehicle.log.services.type').
    service_type_id = fields.Many2one(
        'fleet.service.type',
        string='Service Type',
        copy=True,
        help='Select the type of fleet service to create when confirming this order.'
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
        string='Vehicle',
        copy=False,
        help='Select an existing vehicle for this customer or create a new one.',
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

    # Commission rates entered on each sales order. They are optional and
    # default to 0. Which one is used depends on the selected commission mode.
    revenue_commission_rate = fields.Float(
        string='Revenue Commission (%)',
        default=0.0,
        help='Used by GROSS commission modes from settings.',
    )
    nett_commission_rate = fields.Float(
        string='NETT Commission (%)',
        default=0.0,
        help='Used by NETT commission modes from settings.',
    )
    commission_mode = fields.Selection(
        selection=[
            ('per_product', 'Per Product Commission'),
            ('nett_service', 'NETT Service Commission'),
            ('nett_all', 'NETT All Commission'),
            ('gross_service', 'GROSS Service Commission'),
            ('gross_all', 'GROSS All Commission'),
        ],
        string='Commission Mode',
        compute='_compute_commission_mode',
    )
    show_gross_commission = fields.Boolean(
        string='Show Gross Commission',
        compute='_compute_show_gross_commission',
    )
    commission_amount = fields.Monetary(
        string='Commission Amount',
        currency_field='currency_id',
        compute='_compute_commission_amount',
        store=True,
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

    def _compute_commission_mode(self):
        params = self.env['ir.config_parameter'].sudo()
        param = params.get_param('fleet_sales.commission_mode', default='per_product')
        enable_gross = params.get_param('fleet_sales.enable_gross_commission', default='False') == 'True'
        valid_modes = {
            'per_product',
            'nett_service',
            'nett_all',
            'gross_service',
            'gross_all',
        }
        mode = param if param in valid_modes else 'per_product'
        if not enable_gross and mode in {'gross_service', 'gross_all'}:
            mode = 'per_product'
        for order in self:
            order.commission_mode = mode

    def _compute_show_gross_commission(self):
        enabled = self.env['ir.config_parameter'].sudo().get_param(
            'fleet_sales.enable_gross_commission', default='False'
        ) == 'True'
        for order in self:
            order.show_gross_commission = enabled

    @api.depends(
        'commission_mode',
        'revenue_commission_rate',
        'nett_commission_rate',
        'amount_total',
        'amount_untaxed',
        'order_line.price_total',
        'order_line.price_subtotal',
        'order_line.service_commission_amount',
        'order_line.product_id.type',
    )
    def _compute_commission_amount(self):
        for order in self:
            service_lines = order.order_line.filtered(
                lambda l: l.product_id and l.product_id.type == 'service'
            )
            gross_service_base = sum(service_lines.mapped('price_total'))
            nett_service_base = sum(service_lines.mapped('price_subtotal'))

            if order.commission_mode == 'per_product':
                order.commission_amount = sum(order.order_line.mapped('service_commission_amount'))
            elif order.commission_mode == 'nett_service':
                order.commission_amount = nett_service_base * (order.nett_commission_rate / 100.0)
            elif order.commission_mode == 'nett_all':
                order.commission_amount = order.amount_untaxed * (order.nett_commission_rate / 100.0)
            elif order.commission_mode == 'gross_service':
                order.commission_amount = gross_service_base * (order.revenue_commission_rate / 100.0)
            else:
                order.commission_amount = order.amount_total * (order.revenue_commission_rate / 100.0)

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

        # Step 2: Determine the service type.
        # Priority:
        # 1) Task selected on a service order line
        # 2) Header-level service type
        # 3) "Dedicated" fallback
        # 4) First available service type
        line_task = self.order_line.filtered(
            lambda l: l.product_id and l.product_id.type == 'service' and l.service_task_id
        )[:1].service_task_id
        service_type = line_task or self.service_type_id
        if not service_type:
            service_type = self.env['fleet.service.type'].search(
                [('name', '=', 'Dedicated')], limit=1
            )
        if not service_type:
            service_type = self.env['fleet.service.type'].search([], limit=1)

        # Step 3: Create the fleet service linked to the vehicle and this SO.
        # 'service_type_id' is a required field on fleet.vehicle.log.services.
        service_vals = {
            'vehicle_id': vehicle.id,
            'sale_order_id': self.id,
            'description': _('Service from Sales Order %s') % self.name,
            'date': self.service_date or fields.Date.today(),
            'company_id': self.company_id.id,
            'service_type_id': service_type.id if service_type else False,
        }
        service = self.env['fleet.vehicle.log.services'].create(service_vals)

        # Step 4: Link both records back to this sales order
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
        Uses _for_xml_id() to fetch the original fleet action defined by the
        fleet module, then overrides it to show only the specific record in form view.
        This is the canonical Odoo pattern — it ensures the correct views,
        context, and permissions are used.
        """
        self.ensure_one()
        # Fetch the base action defined in fleet module's XML
        action = self.env['ir.actions.act_window']._for_xml_id('fleet.fleet_vehicle_action')
        # Override to show only the form view for this specific vehicle
        action['views'] = [(False, 'form')]
        action['res_id'] = self.fleet_vehicle_id.id
        action['context'] = {'create': False}
        return action

    def action_open_selected_vehicle_page(self):
        """Open the selected vehicle in the internal sales/fleet route."""
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
        """Open the fleet service form view.
        
        Called when the user clicks the 'Service' smart button on the SO form.
        Uses _for_xml_id() to fetch the standard fleet service action, ensuring
        the correct form view and field visibility are applied.
        """
        self.ensure_one()
        # Fetch the base action for fleet services defined in fleet module
        action = self.env['ir.actions.act_window']._for_xml_id('fleet.fleet_vehicle_log_services_action')
        # Override to show only the form view for this specific service
        action['views'] = [(False, 'form')]
        action['res_id'] = self.fleet_service_id.id
        action['context'] = {'create': False}
        return action


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    service_task_id = fields.Many2one(
        'fleet.service.type',
        string='Task',
        help='Task/service type for this line. Available for service products.',
    )
    service_commission_rate = fields.Float(
        string='Commission (%)',
        default=0.0,
        help='Default comes from the product. You can edit it per line.',
    )
    service_commission_amount = fields.Monetary(
        string='Commission Amount',
        currency_field='currency_id',
        compute='_compute_service_commission_amount',
        store=True,
    )

    @api.depends('price_subtotal', 'service_commission_rate', 'product_id.type')
    def _compute_service_commission_amount(self):
        for line in self:
            if line.product_id and line.product_id.type == 'service':
                line.service_commission_amount = line.price_subtotal * (line.service_commission_rate / 100.0)
            else:
                line.service_commission_amount = 0.0

    @api.onchange('product_id')
    def _onchange_product_id_service_commission_rate(self):
        for line in self:
            if line.product_id and line.product_id.type == 'service':
                line.service_commission_rate = line.product_id.product_tmpl_id.service_commission_rate
            else:
                line.service_commission_rate = 0.0
                line.service_task_id = False

    @api.model_create_multi
    def create(self, vals_list):
        Product = self.env['product.product']
        for vals in vals_list:
            if 'service_commission_rate' in vals:
                continue
            product_id = vals.get('product_id')
            if not product_id:
                continue
            product = Product.browse(product_id)
            if product and product.type == 'service':
                vals['service_commission_rate'] = product.product_tmpl_id.service_commission_rate
            else:
                vals['service_commission_rate'] = 0.0
        return super().create(vals_list)
