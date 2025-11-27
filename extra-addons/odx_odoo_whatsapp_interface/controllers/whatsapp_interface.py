# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class SetColor(http.Controller):

    @http.route('/select_colors', auth='public', type='json')
    def get_colors(self):
        colors = {'background_color': request.env[
            'ir.config_parameter'].sudo().get_param(
            'odx_odoo_whatsapp_interface.background_color'),
            'chat_interface_background': request.env.user.company_id.chat_interface_background}
        return colors

    @http.route('/hide_whatsapp_menu', auth='user', type='json')
    def hide_whatsapp_discuss(self):
        hide = request.env['ir.config_parameter'].sudo().get_param('odx_odoo_whatsapp_interface.whatsapp_menu_hide', default=False)
        return {
            'whatsapp_hide': hide
        }


class WhatsappMessageController(http.Controller):

    @http.route('/send_whatsappMessageType', type='json', auth='public')
    def fetch_whatsapp_message_type(self, message_id):
        whatsapp_message = request.env['whatsapp.message'].sudo().search([('mail_message_id', '=', message_id)],
                                                                         limit=1)
        if whatsapp_message:
            return {
                'wamessageid': whatsapp_message,
                'mailmessageid': whatsapp_message.mail_message_id,
                'whatsappMessageType': whatsapp_message.message_type,
                'whatsappStatus': whatsapp_message.state,
            }
        return {}
