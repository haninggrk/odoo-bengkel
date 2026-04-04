# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


AUTO_TIMESHEET_PREFIX = 'AUTO_SO_TIMESHEET:'


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
        default=lambda self: self.env['ir.config_parameter'].sudo().get_param(
            'fleet_sales.commission_mode', 'per_product'
        ),
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

    @api.onchange('commission_mode')
    def _onchange_commission_mode(self):
        """Clear the irrelevant rate inputs when the commission mode changes."""
        for order in self:
            if order.commission_mode in ('nett_service', 'nett_all', 'per_product'):
                order.revenue_commission_rate = 0.0
            if order.commission_mode in ('gross_service', 'gross_all', 'per_product'):
                order.nett_commission_rate = 0.0
            if order.commission_mode != 'per_product':
                order.order_line.write({'service_commission_rate': 0.0})

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
            mode = order.commission_mode or 'per_product'
            service_lines = order.order_line.filtered(
                lambda l: l.product_id and l.product_id.type == 'service'
            )
            gross_service_base = sum(service_lines.mapped('price_total'))
            nett_service_base = sum(service_lines.mapped('price_subtotal'))

            if mode == 'per_product':
                order.commission_amount = sum(order.order_line.mapped('service_commission_amount'))
            elif mode == 'nett_service':
                order.commission_amount = nett_service_base * (order.nett_commission_rate / 100.0)
            elif mode == 'nett_all':
                order.commission_amount = order.amount_untaxed * (order.nett_commission_rate / 100.0)
            elif mode == 'gross_service':
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
        for order in self:
            missing_employee_lines = order.order_line.filtered(
                lambda l: not l.display_type and l.product_id and l.product_id.type == 'service' and not l.assigned_employee_id
            )
            if missing_employee_lines:
                raise ValidationError(
                    _('Please assign Employee on all service lines before confirming this Sales Order.')
                )
            # Validate group membership: employee must be in the project's fleet group
            for line in order.order_line.filtered(
                lambda l: not l.display_type and l.product_id and l.product_id.type == 'service' and l.assigned_employee_id
            ):
                group = line.line_project_fleet_group_id
                if group and line.assigned_employee_id.user_id:
                    self.env.cr.execute(
                        "SELECT 1 FROM res_groups_users_rel WHERE gid = %s AND uid = %s",
                        [group.id, line.assigned_employee_id.user_id.id]
                    )
                    if not self.env.cr.fetchone():
                        raise ValidationError(_(
                            'Employee "%s" is not a member of the required group "%s" '
                            'for project "%s". Please assign a qualified employee.',
                            line.assigned_employee_id.name,
                            group.sudo().full_name,
                            (line.product_id.project_id or order._get_default_timesheet_project()).name,
                        ))
                elif group and not line.assigned_employee_id.user_id:
                    raise ValidationError(_(
                        'Employee "%s" has no linked user and cannot be verified against '
                        'the required group "%s". Please link a user to this employee.',
                        line.assigned_employee_id.name,
                        group.full_name,
                    ))

        result = super().action_confirm()

        for order in self:
            # Only create a service if:
            # 1. A license plate was provided (the user wants fleet integration)
            # 2. No service has been created yet (avoid duplicates on re-confirmation)
            if order.license_plate and not order.fleet_service_id:
                order._create_fleet_service()
            order._create_service_line_tasks_and_timesheets()

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
        # Use the one selected by the user, or default to "Dedicated",
        # or fall back to the first available service type.
        service_type = self.service_type_id
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
            'amount': self.amount_total,
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

    def _get_default_timesheet_project(self):
        self.ensure_one()
        params = self.env['ir.config_parameter'].sudo()
        project_id = params.get_param('fleet_sales.default_timesheet_project_id')  # stored by timesheet_project_id field
        if project_id:
            project = self.env['project.project'].browse(int(project_id))
            if project.exists():
                return project
        return self.env['project.project'].search([], limit=1)

    def _create_service_line_tasks_and_timesheets(self):
        self.ensure_one()
        service_lines = self.order_line.filtered(
            lambda l: l.product_id and l.product_id.type == 'service' and l.assigned_employee_id
        )
        for line in service_lines:
            self._ensure_line_task_and_timesheet(line)

    def _ensure_line_task_and_timesheet(self, line):
        self.ensure_one()
        if not (line.product_id and line.product_id.type == 'service' and line.assigned_employee_id):
            return

        # Prefer the project set directly on the product; fall back to global setting
        product_project = False
        if 'project_id' in self.env['product.template']._fields:
            product_project = line.product_id.project_id
        project = product_project or self._get_default_timesheet_project()
        if not project:
            return

        Task = self.env['project.task']
        AnalyticLine = self.env['account.analytic.line']

        if not line.generated_task_id:
            user_ids = []
            if line.assigned_employee_id.user_id:
                user_ids = [line.assigned_employee_id.user_id.id]

            task_vals = {
                'name': '%s - %s' % (self.name, line.name or line.product_id.display_name),
                'project_id': project.id,
                'partner_id': self.partner_id.id,
                'user_ids': [(6, 0, user_ids)],
            }
            if 'sale_line_id' in Task._fields:
                task_vals['sale_line_id'] = line.id
            line.generated_task_id = Task.create(task_vals).id

        if line.assigned_employee_id.user_id and line.generated_task_id:
            line.generated_task_id.user_ids = [(6, 0, [line.assigned_employee_id.user_id.id])]

        auto_timesheets = AnalyticLine.search([
            ('task_id', '=', line.generated_task_id.id),
            ('name', '=like', '%s%%' % AUTO_TIMESHEET_PREFIX),
        ])
        if auto_timesheets:
            vals = {
                'employee_id': line.assigned_employee_id.id,
                'date': self.service_date or fields.Date.today(),
                'fleet_so_line_id': line.id,
            }
            if 'so_line' in AnalyticLine._fields:
                vals['so_line'] = line.id
            if line.assigned_employee_id.user_id:
                vals['user_id'] = line.assigned_employee_id.user_id.id
            auto_timesheets.write(vals)
            return

        ts_vals = {
            'name': '%s %s' % (AUTO_TIMESHEET_PREFIX, self.name),
            'project_id': project.id,
            'task_id': line.generated_task_id.id,
            'employee_id': line.assigned_employee_id.id,
            'date': self.service_date or fields.Date.today(),
            'unit_amount': 0.0,
            'company_id': self.company_id.id,
            'fleet_so_line_id': line.id,
        }
        if 'so_line' in AnalyticLine._fields:
            ts_vals['so_line'] = line.id
        if line.assigned_employee_id.user_id:
            ts_vals['user_id'] = line.assigned_employee_id.user_id.id
        AnalyticLine.create(ts_vals)

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


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    assigned_employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        help='Employee assigned to this service line. A task and timesheet are auto-created on confirmation.',
    )
    generated_task_id = fields.Many2one(
        'project.task',
        string='Generated Task',
        readonly=True,
        copy=False,
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
    line_project_fleet_group_id = fields.Many2one(
        'res.groups',
        string='Project Fleet Group',
        compute='_compute_line_project_fleet_group_id',
        store=False,
    )
    line_allowed_employee_ids = fields.Many2many(
        'hr.employee',
        compute='_compute_line_allowed_employees',
        store=False,
        string='Allowed Employees',
    )

    @api.depends('product_id')
    def _compute_line_project_fleet_group_id(self):
        for line in self:
            project = False
            if 'project_id' in self.env['product.template']._fields:
                project = line.product_id.project_id
            if not project:
                project = line.order_id._get_default_timesheet_project()
            line.line_project_fleet_group_id = project.fleet_group_id if project else False

    @api.depends('product_id')
    def _compute_line_allowed_employees(self):
        Employee = self.env['hr.employee']
        for line in self:
            group = line.line_project_fleet_group_id
            if group:
                self.env.cr.execute(
                    "SELECT uid FROM res_groups_users_rel WHERE gid = %s",
                    [group.id]
                )
                user_ids = [row[0] for row in self.env.cr.fetchall()]
                line.line_allowed_employee_ids = Employee.search([('user_id', 'in', user_ids)]) if user_ids else Employee
            else:
                line.line_allowed_employee_ids = Employee

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
                line.assigned_employee_id = False

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
        lines = super().create(vals_list)
        for line in lines:
            if line.order_id.state in {'sale', 'done'}:
                line.order_id._ensure_line_task_and_timesheet(line)
        return lines

    def write(self, vals):
        res = super().write(vals)
        tracked_fields = {'assigned_employee_id', 'product_id', 'product_uom_qty', 'name'}
        if tracked_fields.intersection(vals.keys()):
            for line in self:
                if line.order_id.state in {'sale', 'done'}:
                    line.order_id._ensure_line_task_and_timesheet(line)
        return res
