# -*- coding: utf-8 -*-
from odoo import api, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def get_user_images(self):
        return self.env.user.partner_id.image_1920
