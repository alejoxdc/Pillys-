from odoo import fields, models, api
from odoo.tools.translate import _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import logging
_logger = logging.getLogger(__name__)
class Partner(models.Model):
    _inherit = "res.partner"

    @api.model
    def create_from_ui(self, partner):
        _logger.error(partner)
        if partner.get('country_id'):
            partner['country_id'] = int(partner.get('country_id'))
        if partner.get('vat'):
            partner['vat_co'] = partner.get('vat')
            if not partner['fiscal_responsability_ids']:
                partner['fiscal_responsability_ids'] = [(6, 0, [7])]
        if partner.get('state_id'):
            partner['state_id'] = int(partner.get('state_id'))
        return super().create_from_ui(partner)