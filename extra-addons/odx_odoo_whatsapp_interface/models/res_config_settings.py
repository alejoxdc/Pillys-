# -*- coding: utf-8 -*-
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    background_color = fields.Char(string='Background Color',
                                   config_parameter='odx_odoo_whatsapp_interface.background_color',
                                   default='#EBE5DE',
                                   help='Select discuss background color')
    chat_interface_background = fields.Binary(string="Background Image",
                                              related='company_id.chat_interface_background',
                                              readonly=False,
                                              help='Add background image for discuss')
    whatsapp_menu_hide = fields.Boolean(string="Hide WhatsApp Channel from Discuss",
                                        config_parameter='odx_odoo_whatsapp_interface.whatsapp_menu_hide',
                                        help='Hide WhatsApp Menu in discuss')
