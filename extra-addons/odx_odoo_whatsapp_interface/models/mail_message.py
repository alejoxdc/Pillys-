# -*- coding: utf-8 -*-
from odoo import fields, models

class MailMessage(models.Model):
    _inherit = "mail.message"

    whatsapp_message_type = fields.Char(string="whatsapp_message_type")

    def message_format(self, *args, **kwargs):
        vals_list = super(MailMessage, self).message_format(*args, **kwargs)

        whatsapp_mail_message = self.filtered(lambda m: m.message_type == 'whatsapp_message')
        if whatsapp_mail_message:
            for vals in vals_list:

                message_record = self.browse(vals['id'])
                if message_record.wa_message_ids:
                    vals['whatsappMessageType'] = message_record.wa_message_ids.message_type

        return vals_list
