from odoo import models, fields

class MessageWarning(models.Model):
    _name = 'whatsapp_chatbot.message.warning'
    _description = 'Warning Message'

    text = fields.Text(string='Message')