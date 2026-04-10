# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


AUTO_TIMESHEET_PREFIX = 'AUTO_SO_TIMESHEET:'


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        for order in self:
            for line in order.order_line.filtered(
                lambda l: not l.display_type and l.product_id and l.product_id.type == 'service' and l.assigned_employee_id
            ):
                group = line.line_project_sales_group_id
                if group and line.assigned_employee_id.user_id:
                    self.env.cr.execute(
                        'SELECT 1 FROM res_groups_users_rel WHERE gid = %s AND uid = %s',
                        [group.id, line.assigned_employee_id.user_id.id],
                    )
                    if not self.env.cr.fetchone():
                        raise ValidationError(_(
                            'Employee "%s" is not a member of the required group "%s" for project "%s". Please assign a qualified employee.',
                            line.assigned_employee_id.name,
                            group.sudo().full_name,
                            (line.product_id.project_id or order._get_default_timesheet_project()).name,
                        ))
                elif group and not line.assigned_employee_id.user_id:
                    raise ValidationError(_(
                        'Employee "%s" has no linked user and cannot be verified against the required group "%s". Please link a user to this employee.',
                        line.assigned_employee_id.name,
                        group.full_name,
                    ))

        result = super().action_confirm()
        for order in self:
            order._create_service_line_tasks_and_timesheets()
        return result

    def _get_default_timesheet_project(self):
        self.ensure_one()
        params = self.env['ir.config_parameter'].sudo()
        project_id = params.get_param('kedoo_sales_timesheet_assignment.default_project_id')
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

        product_project = False
        if 'project_id' in self.env['product.template']._fields:
            product_project = line.product_id.project_id
        project = product_project or self._get_default_timesheet_project()
        if not project:
            return

        Task = self.env['project.task']
        AnalyticLine = self.env['account.analytic.line']

        if not line.generated_task_id:
            existing_task = False
            if 'task_id' in line._fields and line.task_id:
                existing_task = line.task_id
            elif 'sale_line_id' in Task._fields:
                existing_task = Task.search([('sale_line_id', '=', line.id)], limit=1)

            if existing_task:
                line.generated_task_id = existing_task.id
                if 'sale_line_id' in Task._fields and not existing_task.sale_line_id:
                    existing_task.sale_line_id = line.id

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
                'date': self.date_order or fields.Date.today(),
                'sales_service_line_id': line.id,
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
            'date': self.date_order or fields.Date.today(),
            'unit_amount': 0.0,
            'company_id': self.company_id.id,
            'sales_service_line_id': line.id,
        }
        if 'so_line' in AnalyticLine._fields:
            ts_vals['so_line'] = line.id
        if line.assigned_employee_id.user_id:
            ts_vals['user_id'] = line.assigned_employee_id.user_id.id
        AnalyticLine.create(ts_vals)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    assigned_employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        help='Employee assigned to this service line. Task and timesheet are auto-created on confirmation.',
    )
    generated_task_id = fields.Many2one(
        'project.task',
        string='Generated Task',
        readonly=True,
        copy=False,
    )
    line_project_sales_group_id = fields.Many2one(
        'res.groups',
        string='Project Assignment Group',
        compute='_compute_line_project_sales_group_id',
        store=False,
    )
    line_allowed_employee_ids = fields.Many2many(
        'hr.employee',
        compute='_compute_line_allowed_employees',
        store=False,
        string='Allowed Employees',
    )

    @api.depends('product_id')
    def _compute_line_project_sales_group_id(self):
        for line in self:
            project = False
            if 'project_id' in self.env['product.template']._fields:
                project = line.product_id.project_id
            if not project:
                project = line.order_id._get_default_timesheet_project()
            line.line_project_sales_group_id = project.sales_assignment_group_id if project else False

    @api.depends('product_id')
    def _compute_line_allowed_employees(self):
        Employee = self.env['hr.employee']
        for line in self:
            group = line.line_project_sales_group_id
            if group:
                self.env.cr.execute(
                    'SELECT uid FROM res_groups_users_rel WHERE gid = %s',
                    [group.id]
                )
                user_ids = [row[0] for row in self.env.cr.fetchall()]
                line.line_allowed_employee_ids = Employee.search([('user_id', 'in', user_ids)]) if user_ids else Employee
            else:
                line.line_allowed_employee_ids = Employee

    @api.model_create_multi
    def create(self, vals_list):
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
