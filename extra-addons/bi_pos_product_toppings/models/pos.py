from odoo import api, fields, models, _
import json


class ProductProduct(models.Model):
	_inherit = 'product.product'

	is_topping = fields.Boolean(string="Is Topping")
	topping_group_ids = fields.Many2many("topping.groups",string="Topping Groups")
	topping_ids = fields.Many2many("product.product",'rel_prod_prod_db','p1','p2',string="Toppings",domain=[("is_topping","=",True)])

	@api.onchange('topping_group_ids')
	def onchange_topping_group_ids(self):
		self.topping_ids = [(6,0,self.topping_group_ids.topping_ids.ids)]
		

class ToppingGroups(models.Model):
	_name = 'topping.groups'
	_description = "Topping Groups"

	name = fields.Char('Name', required=True)
	topping_ids = fields.Many2many("product.product",'rel_prod_tg_db','tg_id','prod_id',string="Toppings",domain=[("is_topping","=",True)])


class PosCategory(models.Model):
	_inherit = 'pos.category'

	topping_ids = fields.Many2many("product.product",'rel_prod_categ_db','categ_id','prod_id',string="Toppings",domain=[("is_topping","=",True)])


class PosConfig(models.Model):
	_inherit = 'pos.config'

	activate_toppings = fields.Boolean('Enable Product Toppings')
	add_topping_default = fields.Boolean('Add toppings on product add')


class ResConfigSettings(models.TransientModel):
	_inherit = 'res.config.settings'

	activate_toppings = fields.Boolean(related='pos_config_id.activate_toppings',readonly=False)
	add_topping_default = fields.Boolean(related='pos_config_id.add_topping_default',readonly=False)


class pos_order(models.Model):
	_inherit = 'pos.order'

	@api.model
	def _process_order(self, order, draft, existing_order):
		odr = order['data']
		new_lines = []
		for lines in odr['lines']:
			toppingdata = lines[2].get('toppingdata',False)
			combo_list = []
			if toppingdata:
				for product in toppingdata:
					vals =  [0, 0, {
						'qty': product.get('qty',1),
						'price_unit': 0,
						'price_subtotal': 0,
						'price_subtotal_incl': 0,
						'discount': 0,
						'product_id': product.get('id',False),
						'tax_ids': [[6, False, []]],
						'full_product_name': product.get('name',"-"),
						'name': product.get('name',"-"),
					}]
					new_lines.append(vals)
		# order['data']['lines'].extend(new_lines)
		return super(pos_order, self)._process_order(order, draft, existing_order)

	def _process_preparation_changes(self, cancelled=False, note_history=None):
		self.ensure_one()
		flag_change = False
		sound = False

		pdis_order = self.env['pos_preparation_display.order'].search(
			[('pos_order_id', '=', self.id)]
		)

		pdis_lines = pdis_order.preparation_display_order_line_ids
		pdis_ticket = False
		quantity_data = {}
		category_ids = set()

		# If cancelled flag, we flag all lines as cancelled
		if cancelled:
			for line in pdis_lines:
				line.product_cancelled = line.product_quantity
				category_ids.update(line.product_id.pos_categ_ids.ids)
			return {'change': True, 'sound': sound, 'category_ids': category_ids}

		# create a dictionary with the key as a tuple of product_id, internal_note and attribute_value_ids
		for pdis_line in pdis_lines:
			key = (pdis_line.product_id.id, pdis_line.internal_note or '', json.dumps(pdis_line.attribute_value_ids.ids),json.dumps(pdis_line.line_topping_ids.ids))
			line_qty = pdis_line.product_quantity - pdis_line.product_cancelled
			if not quantity_data.get(key):
				quantity_data[key] = {
					'attribute_value_ids': pdis_line.attribute_value_ids.ids,
					'line_topping_ids': pdis_line.line_topping_ids.ids,
					'note': pdis_line.internal_note or '',
					'product_id': pdis_line.product_id.id,
					'display': line_qty,
					'order': 0,
				}
			else:
				quantity_data[key]['display'] += line_qty

		for line in self.lines.filtered(lambda li: not li.skip_change):
			line_note = self._get_line_note(line)
			key = (line.product_id.id, line_note, json.dumps(line.attribute_value_ids.ids), json.dumps(line.line_topping_ids.ids))

			if not quantity_data.get(key):
				quantity_data[key] = {
					'attribute_value_ids': line.attribute_value_ids.ids,
					'line_topping_ids': line.line_topping_ids.ids,
					'note': line_note or '',
					'product_id': line.product_id.id,
					'display': 0,
					'order': line.qty,
				}
			else:
				quantity_data[key]['order'] += line.qty

		# Update quantity_data with note_history
		if note_history:
			for line in pdis_lines[::-1]:
				product_id = str(line.product_id.id)
				for note in note_history.get(product_id, []):
					if line.internal_note == note['old'] and note['qty'] > 0 and line.product_quantity <= note['qty'] - note.get('used_qty', 0):
						if not note.get('used_qty'):
							note['used_qty'] = line.product_quantity
						else:
							note['used_qty'] += line.product_quantity

						key = (line.product_id.id, line.internal_note or '', json.dumps(line.attribute_value_ids.ids), json.dumps(line.line_topping_ids.ids))
						key_new = (line.product_id.id, note['new'] or '', json.dumps(line.attribute_value_ids.ids), json.dumps(line.line_topping_ids.ids))

						line.internal_note = note['new']
						flag_change = True
						category_ids.update(line.product_id.pos_categ_ids.ids)

						# Merge the two lines, so that if the quantity was changed it's also applied
						old_quantity = quantity_data.pop(key, None)
						if old_quantity:
							if key_new in quantity_data:
								quantity_data[key_new]["display"] += old_quantity["display"]
								quantity_data[key_new]["order"] += old_quantity["order"]
							else:
								quantity_data[key_new] = old_quantity

		# Check if pos_order have new lines or if some lines have more quantity than before
		if any([quantities['order'] > quantities['display'] for quantities in quantity_data.values()]):
			is_not_splitted_order = not self.env.context.get("is_splited_order")
			flag_change = is_not_splitted_order
			sound = is_not_splitted_order
			pdis_ticket = self.env['pos_preparation_display.order'].create({
				'displayed': is_not_splitted_order,
				'pos_order_id': self.id,
				'pos_config_id': self.config_id.id,
			})

		product_ids = self.env['product.product'].browse([data['product_id'] for data in quantity_data.values()])
		for data in quantity_data.values():
			product_id = data['product_id']
			product = product_ids.filtered(lambda p: p.id == product_id)
			if data['order'] > data['display']:
				missing_qty = data['order'] - data['display']
				filtered_lines = self.lines.filtered(lambda li: li.product_id.id == product_id and self._get_line_note(li) == data['note'] and li.attribute_value_ids.ids == data['attribute_value_ids'])
				line_qty = 0
				for line in filtered_lines:

					if missing_qty == 0:
						break

					if missing_qty > line.qty:
						line_qty += line.qty
						missing_qty -= line.qty
					elif missing_qty <= line.qty:
						line_qty += missing_qty
						missing_qty = 0

					if missing_qty == 0 and line_qty > 0:
						flag_change = True
						category_ids.update(product.pos_categ_ids.ids)
						self.env['pos_preparation_display.orderline'].create({
							'todo': True,
							'internal_note': self._get_line_note(line),
							'attribute_value_ids': line.attribute_value_ids.ids,
							'line_topping_ids': line.line_topping_ids.ids,
							'product_id': product_id,
							'product_quantity': line_qty,
							'preparation_display_order_id': pdis_ticket.id,
						})
			elif data['order'] < data['display']:
				qty_to_cancel = data['display'] - data['order']
				for line in pdis_lines.filtered(lambda li: li.product_id.id == product_id and li.internal_note == data['note'] and li.attribute_value_ids.ids == data['attribute_value_ids']):
					flag_change = True
					line_qty = 0
					pdis_qty = line.product_quantity - line.product_cancelled

					if qty_to_cancel == 0:
						break

					if pdis_qty > qty_to_cancel:
						line.product_cancelled += qty_to_cancel
						qty_to_cancel = 0
					elif pdis_qty <= qty_to_cancel:
						line.product_cancelled += pdis_qty
						qty_to_cancel -= pdis_qty

		return {'change': flag_change, 'sound': sound, 'category_ids': category_ids}


class POSSession(models.Model):
	_inherit = 'pos.session'

	def _pos_ui_models_to_load(self):
		result = super()._pos_ui_models_to_load()
		result.extend(['topping.groups'])
		return result

	def _loader_params_topping_groups(self):
		return {
			'search_params': {
				'domain': [], 
				'fields': ['name','id','topping_ids'],
			}
		}

	def _get_pos_ui_topping_groups(self, params):
		return self.env['topping.groups'].search_read(**params['search_params'])

	def _loader_params_product_product(self):
		res = super(POSSession, self)._loader_params_product_product()
		fields = res.get('search_params').get('fields')
		fields.extend(['is_topping','topping_group_ids','topping_ids'])
		res['search_params']['fields'] = fields
		return res

	def _loader_params_pos_category(self):
		res = super(POSSession, self)._loader_params_pos_category()
		fields = res.get('search_params').get('fields')
		fields.extend(['topping_ids'])
		res['search_params']['fields'] = fields
		return res

	def _pos_data_process(self, loaded_data):
		super()._pos_data_process(loaded_data)

		loaded_data['topping_group_by_id'] = {ppp['id']: ppp for ppp in loaded_data['topping.groups']}
		topping_prods = {}
		for prods in loaded_data['product.product']:
			if prods.get('is_topping',False) :
				topping_prods.update({
					prods['id']: prods
				})
		loaded_data['toppings_by_id'] = topping_prods


class pos_order_line(models.Model):
	_inherit = 'pos.order.line'

	line_topping_ids = fields.Many2many("product.product",string="Product Toppings")


	def _export_for_ui(self, order):
		result = super(pos_order_line, self)._export_for_ui(order)
		result['line_topping_ids'] = order.line_topping_ids.ids
		return result

	def _order_line_fields(self, line, session_id=None):
		result = super()._order_line_fields(line, session_id)
		vals = result[2]
		if 'line_topping_ids' in vals:
			vals['line_topping_ids'] = vals['line_topping_ids']
		return result