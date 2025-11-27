# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'
    _description = "Res Users"
    
    is_patient = fields.Boolean('Is Patient?')
    is_doctor = fields.Boolean('Is Doctor?')


    @api.model
    def create(self, vals):
        user = super(ResUsers, self).create(vals)
        if user.is_doctor:
            self.env['medical.physician'].create({
                'res_partner_physician_id': user.partner_id.id,
                'speciality': 58,
            })

        return user