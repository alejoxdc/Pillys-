from odoo import models, fields, api
from odoo.exceptions import ValidationError

class WhatsappQuickResponse(models.Model):
    _name = 'whatsapp.quick.response'
    _description = 'WhatsApp Quick Response'

    name = fields.Char(string='Name', required=True)
    type = fields.Selection([
        ('text', 'Text'),
        ('file', 'File')
    ], string='Type', required=True, default='text')
    text_content = fields.Text(string='Text Content')

    @api.constrains('type', 'text_content')
    def _check_text_content(self):
        for record in self:
            if record.type == 'text' and not record.text_content:
                raise ValidationError("Text content must be provided for type 'text'.")

    def search_for_quick_response(self, message,limit=100):
        quick_responses = self.env['whatsapp.quick.response'].search([
            ('name', 'ilike', message),
        ], limit=limit)
        quick_responses_list = []
        
        # for each template, get the template name and id and add it to the templates_list as objects
        for quick_response in quick_responses:
            quick_responses_list.append({
                "body": quick_response.text_content,
                "name": quick_response.name,
                "id": quick_response.id,
            })
        
        # return an array of template objects
        return quick_responses_list