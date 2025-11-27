from odoo import http
from odoo.http import request

class WebhookController(http.Controller):

    @http.route('/webhook', type='json', auth='public', methods=['POST'], csrf=False)
    def webhook_handler(self, **kwargs):
        data = request.jsonrequest
        if 'message' in data:
            message = data['message']
            whatsapp_integration = request.env['whatsapp.integration']
            chatbot = request.env['chatbot']
            whatsapp_integration.handle_incoming_message(message)
            chatbot_response = chatbot.generate_response(message)
            whatsapp_integration.send_message(chatbot_response)
        return {}