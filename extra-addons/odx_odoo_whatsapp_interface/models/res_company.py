# -*- coding: utf-8 -*-
import base64
from odoo import fields, models, api
from odoo.tools import  file_open

class ResCompany(models.Model):
    _inherit = 'res.company'


    chat_interface_background = fields.Binary(string="WhatsApp Channel Background Image",
                                     help='Background image for WhatsApp channel')

    def _get_chat_interface_background(self):
        with file_open('odx_odoo_whatsapp_interface/static/src/img/whatsapp_background.jpg', 'rb') as file:
            return base64.b64encode(file.read())

    @api.model
    def _update_whatsapp_bg_image(self, vals=None):
        companies = self.env['res.company'].sudo().search([])
        for rec in companies:
            if not rec.chat_interface_background:
                rec.chat_interface_background = self._get_chat_interface_background()
        return  True
