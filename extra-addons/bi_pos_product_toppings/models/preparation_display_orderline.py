from odoo import api, fields, models, _


class PosPreparationDisplayOrderline(models.Model):
	_inherit = 'pos_preparation_display.orderline'

	line_topping_ids = fields.Many2many('product.product', string="Selected Topping")


class PosPreparationDisplayOrder(models.Model):
	_inherit = 'pos_preparation_display.order'


	def _export_for_ui(self, preparation_display):
		preparation_display_orderlines = []

		for orderline in self.preparation_display_order_line_ids:
			if preparation_display._should_include(orderline):
				preparation_display_orderlines.append({
					'id': orderline.id,
					'todo': orderline.todo,
					'internal_note': orderline.internal_note,
					'attribute_ids': orderline.attribute_value_ids.ids,
					'line_topping_ids': orderline.line_topping_ids.ids,
					'product_id': orderline.product_id.id,
					'product_name': orderline.product_id.display_name,
					'product_quantity': orderline.product_quantity,
					'product_cancelled': orderline.product_cancelled,
					'product_category_ids': orderline.product_id.pos_categ_ids.ids,
				})

		if preparation_display_orderlines:
			current_order_stage = None

			for stage in self.order_stage_ids[::-1]:
				if stage.preparation_display_id.id == preparation_display.id:
					current_order_stage = stage
					break

			return {
				'id': self.id,
				'pos_order_id': self.pos_order_id.id,
				'create_date': self.create_date,
				'responsible': self.create_uid.display_name,
				'stage_id': current_order_stage.stage_id.id if current_order_stage else None,
				'last_stage_change': current_order_stage.write_date if current_order_stage else self.create_date,
				'displayed': self.displayed,
				'orderlines': preparation_display_orderlines,
				'tracking_number': self.pos_order_id.tracking_number,
			}


class PosPreparationDisplay(models.Model):
	_inherit = 'pos_preparation_display.display'


	def get_preparation_display_data(self):
		return {
			'categories': self._get_pos_category_ids().read(['id', 'display_name', 'sequence']),
			'stages': self.stage_ids.read(),
			'orders': self.env["pos_preparation_display.order"].get_preparation_display_order(self.id),
			'attributes': self.env['product.attribute'].search([]).read(['id', 'name']),
			'all_products': self.env['product.product'].search([]).read(['id', 'display_name']),
			'attribute_values': self.env['product.template.attribute.value'].search([]).read(['id', 'name', 'attribute_id']),
		}