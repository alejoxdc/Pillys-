# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
	'name': 'POS Product Toppings | POS Product Modifier',
	'version': '17.0.0.4',
	'category': 'Point of Sale',
	'summary': 'Point of sales product Toppings point of sales product Modifier pos Toppings pos Modifier pos product group modifier pos pizza modifier pos pizza maker pos own pizza maker pos combo meal pos product combo point of sale combo meal on pos meal toppings',
	'description' :"""
		This odoo app will help the fast food businesses where the snacks toppings are there. Users can create different toppings for products, create topping groups with different toppings, add topping groups to products, the same products can have different toppings, and also mass update toppings for products. Users have the option to select and add toppings from the pos screen and the toppings price will be added to the main product, user also has the option to automatically add all toppings to the cart that are added to the main products and printed to the pos receipt.
	""",
	'author': 'BrowseInfo',
	'website': 'https://www.browseinfo.com',
	"price": 25,
	"currency": 'EUR',
	'depends': ['base','point_of_sale','pos_restaurant','pos_preparation_display'],
	'data': [
		'security/ir.model.access.csv',
		'views/pos_config_inherit.xml',
		'wizard/topping_wizard_view.xml',
	],
	'assets': {
		'point_of_sale._assets_pos': [
			"bi_pos_product_toppings/static/src/js/models.js",
			"bi_pos_product_toppings/static/src/js/ToppingsButton.js",
			"bi_pos_product_toppings/static/src/js/ToppingPopup.js",
			'bi_pos_product_toppings/static/src/xml/pos.xml',
		],
		'pos_preparation_display.assets': [
			"bi_pos_product_toppings/static/src/xml/kitchen_display.xml",			
			"bi_pos_product_toppings/static/src/js/Orderline.js",
			"bi_pos_product_toppings/static/src/js/preparation_display.js",
		],

	 },
	'demo': [],
	'test': [],
	'installable': True,
	'auto_install': False,
	'live_test_url':'https://youtu.be/tdFrEtulpHE',
	"images":['static/description/Banner.gif'],
	'license': 'OPL-1',
}
