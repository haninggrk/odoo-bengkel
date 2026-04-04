# -*- coding: utf-8 -*-
from odoo import fields, models


class TimesheetsAnalysisReport(models.Model):
    _inherit = 'timesheets.analysis.report'

    fleet_commission_amount = fields.Float(
        string='Commission',
        readonly=True,
        help='Commission amount from Fleet Sales service line.',
    )

    def _select(self):
        return super()._select() + """,
            COALESCE(SOL.service_commission_amount, 0.0) AS fleet_commission_amount
        """

    def _from(self):
        return super()._from() + """
            LEFT JOIN sale_order_line SOL ON A.fleet_so_line_id = SOL.id
        """
