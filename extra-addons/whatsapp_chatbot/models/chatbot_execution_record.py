from odoo import models, fields, api

class ChatbotExecutionRecord(models.Model):
    _name = 'chatbot.execution.record'

    chatbot_id = fields.Many2one('whatsapp_chatbot.chatbot', string='Chatbot')
    channel_id = fields.Many2one('channel', string='Channel')
    partner_id = fields.Many2one('res.partner', string='Partner')
    state = fields.Selection([
        ('ignored', 'Ignored'),
        ('uncompleted', 'Uncompleted'),
        ('completed', 'Completed'),
    ], string='State', default='completed', copy=False)
    execution_time = fields.Datetime(string='Execution Time', default=fields.Datetime.now)

    @api.model
    def create(self, vals):
        record = super(ChatbotExecutionRecord, self).create(vals)
        return record