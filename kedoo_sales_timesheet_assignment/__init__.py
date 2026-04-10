# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api

from . import models


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['project.task.type'].search([]).write({'fold': False})
