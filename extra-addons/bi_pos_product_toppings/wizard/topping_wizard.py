# -*- coding: utf-8 -*-
# Part of Browseinfo. See LICENSE file for full copyright and licensing details.


from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProductToppingWiz(models.TransientModel):
	_name = 'product.topping.add.wizard'
	_description = 'Product Topping Wiz'
	
	topping_group_ids = fields.Many2many("topping.groups",string="Topping Groups")
	topping_ids = fields.Many2many('product.product',domain=[("is_topping","=",True)])

	@api.onchange('topping_group_ids')
	def onchange_topping_group_ids(self):
		self.topping_ids = [(6,0,self.topping_group_ids.topping_ids.ids)]

	def process(self):
		model = self._context.get('active_model')
		rec_ids = self._context.get('active_ids')
		if model == 'product.product' :
			prods = self.env['product.product'].browse(rec_ids)
			prods.write({
				'topping_group_ids' : [(6,0,self.topping_group_ids.ids)],
				'topping_ids' : [(6,0,self.topping_ids.ids)],
			})
