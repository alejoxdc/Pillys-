from odoo import models, fields, api

class WhatsappComposer(models.TransientModel):
    _inherit = 'whatsapp.composer'

    send_chatbot_message = fields.Boolean(string="Send Chatbot Message", default=False)

    def write(self, vals):
        # Check if 'send_chatbot_message' is in vals and it's set to True
        if 'send_chatbot_message' in vals and vals['send_chatbot_message']:
            # Set 'write_uid' to the value of 'create_uid'
            vals['write_uid'] = self.create_uid.id
        return super(WhatsappComposer, self).write(vals)