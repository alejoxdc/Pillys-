# -*- coding: utf-8 -*-
from odoo import fields, models, api
from datetime import timedelta


class IrConfigExtend(models.Model):
    _inherit = "ir.config_parameter"

    def extend_date(self):
        # Fetch the 'database.expiration_date' parameter
        data = self.env['ir.config_parameter'].sudo().search([('key', '=', 'database.expiration_date')])
        if data:
            # Attempt to parse the date
            try:
                expiration_date = fields.Datetime.from_string(data.value)
            except ValueError:
                return  # Exit if parsing fails

            # Extend the expiration date by 365 days
            new_expiration_date = expiration_date + timedelta(days=365)

            # Update the new date in the 'ir.config_parameter'
            data.sudo().write({'value': fields.Datetime.to_string(new_expiration_date)})
