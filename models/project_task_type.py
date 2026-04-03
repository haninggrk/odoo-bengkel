# -*- coding: utf-8 -*-
from odoo import fields, models


class ProjectTaskType(models.Model):
    _inherit = 'project.task.type'

    fold = fields.Boolean(default=False)
