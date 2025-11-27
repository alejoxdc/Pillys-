# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError, AccessError
from odoo.addons import decimal_precision as dp
import json

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.depends('order_line.taxes_id', 'order_line.price_subtotal', 'amount_total', 'amount_untaxed')
    def  _compute_tax_totals(self):

        for order in self:
            order_lines = order.order_line.filtered(lambda x: not x.display_type)
            for tax_id in order_lines.taxes_id:
                if not tax_id.in_order:
                    order_lines.taxes_id = order_lines.taxes_id - tax_id 
            base_line = [x._convert_to_tax_base_line_dict() for x in order_lines]

            order.tax_totals = self.env['account.tax']._prepare_tax_totals(base_line,order.currency_id or order.company_id.currency_id,)    

    
       
class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.depends('discount', 'price_unit')
    def _compute_price_unit_discounted(self):
        for line in self:
            line.price_subtotal = line.price_unit * (1 - line.discount / 100)

