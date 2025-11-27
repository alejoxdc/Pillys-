from odoo import api, fields, models
from random import randint

class UtmCampaignAd(models.Model):
    _name = 'utm.campaign.ad'
    _description = "Anuncio"
    
    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char('Code', required=True, translate=True)
    color = fields.Integer('Color', default=_get_default_color)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "AD Code already exists!"),
    ]

class UtmCampaign(models.Model):
    _inherit = 'utm.campaign'

    meta_id_campaign = fields.Char(string='Meta ID Campaign')
    social_network_name = fields.Selection([
        ('Facebook', 'Facebook'),
        ('Instagram', 'Instagram')
    ], string='Social Network')
    assigned_budget = fields.Float(string='Assigned Budget')
    executed_budget = fields.Float(string='Executed Budget')
    roas = fields.Float(string='ROAS', compute='_compute_roas')
    ad_ids = fields.Many2many("utm.campaign.ad", string="Ads")

    @api.depends('invoiced_amount', 'executed_budget')
    def _compute_roas(self):
        for record in self:
            record.roas = 0
            if record.executed_budget:
                record.roas = record.invoiced_amount / record.executed_budget