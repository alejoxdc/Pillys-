from odoo import models, fields, api

class MailMessage(models.Model):
    _inherit = 'mail.message'

    def get_truncated_body(self, message_id):
        # Retrieve the mail.message record by its ID
        message = self.browse(message_id)
        if not message:
            return False
        # Truncate the body to 15 characters
        truncated_body = message.body[:15]
        return truncated_body