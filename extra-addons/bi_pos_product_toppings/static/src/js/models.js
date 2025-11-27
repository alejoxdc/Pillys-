/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { Order, Orderline } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    // @Override
    async _processData(loadedData) {
        await super._processData(loadedData);
        let self = this;
		self.prod_toppings = loadedData['topping.groups'] || [];
		self.toppings_by_id = loadedData['toppings_by_id'] || [];
		self.topping_group_by_id = loadedData['topping_group_by_id'] || [];
    },
   
});

patch(Order.prototype, {
    setup() {
        super.setup(...arguments);
    },
    add_product(product, options) {
		super.add_product(...arguments);
		if(this.pos.config.activate_toppings && this.pos.config.add_topping_default){

			this._addDefaultToppings();
		}
	},
	// set_partner(partner) {
    //     this.assert_editable();
    //     this.partner = partner;
    // },

    deleteLine(ev){
		let order = this.pos.get_order();
		let orderline = order.get_selected_orderline();
		let toppings = orderline.get_line_topping_ids();
		let y = jQuery.grep(toppings, function(value) {
		  return value != ev.id;
		});
		orderline.set_line_topping_ids(y);
		let details  = orderline.getToppingDetails();
		let ltotal = ev.total;
		orderline.price_type = "manual";
		orderline.set_unit_price(orderline.price - ltotal);
		orderline.price_manually_set = true;
	},


	_addDefaultToppings(){
		if(this.pos.config.activate_toppings && this.pos.config.add_topping_default){
			let orderline = this.selected_orderline;
			let prod = orderline.product;
			let old_rate = orderline.price;

			let arr = prod.topping_ids;
			let aa = arr.filter((item,index) => arr.indexOf(item) === index);
			orderline.set_line_topping_ids(aa);
			let details  = orderline.getToppingDetails();
			let total_arr = details.map(item => item.total);
			let sum = total_arr.reduce((a, b) => a + b, 0) + old_rate;
			// orderline.set_unit_price(sum);
			// orderline.set_price_extra(orderline.toppings_total);
			orderline.price_type = "manual";
			orderline.set_unit_price(sum);
			orderline.price_manually_set = true;
		} 
	}

});

patch(Orderline.prototype, {
	setup() {
        super.setup(...arguments);
        this.line_toppings = this.line_toppings || [];
		this.line_topping_ids = this.line_topping_ids || [];
		this.toppings_total = this.toppings_total || 0;
		this.toppingdata = this.toppingdata || [];
    },

    getDisplayData() {
        return {
            ...super.getDisplayData(),
            toppingsData: this.get_toppingsData() || [],
        };
    },

	set_line_toppings(line_toppings){
		this.order.assert_editable();
		this.line_toppings = line_toppings;
	},

	clone() {
        const orderline = super.clone(...arguments);
        orderline.line_topping_ids = this.line_topping_ids || [];
        return orderline;
    },
	get_line_toppings(){
		return this.line_toppings;
	},

	set_line_topping_ids(line_topping_ids){
		this.order.assert_editable();
		this.line_topping_ids = line_topping_ids;
	},

	get_line_topping_ids(){
		return this.line_topping_ids;
	},

	
	set_toppings_total(toppings_total){
		this.toppings_total = toppings_total;
	},

	get_toppings_total(){
		return this.toppings_total;
	},
		
	init_from_JSON(json){
		super.init_from_JSON(...arguments);
		this.line_toppings = json.line_toppings || [];
		this.line_topping_ids = json.line_topping_ids || [];
		this.toppings_total = json.toppings_total || 0;
	},

	export_as_JSON(){
		const json = super.export_as_JSON(...arguments);
		json.line_toppings = this.getToppingDetails() || [];
		json.toppingdata = this.toppingdata || [];
		json.line_topping_ids = this.line_topping_ids || [];
		json.toppings_total = this.get_toppings_total() || 0;
		return json;
	},

	export_for_printing() {
		const json = super.export_for_printing(...arguments);
		json.toppingdata = this.toppingdata || [];
		json.line_topping_ids = this.line_topping_ids || [];
		json.toppings_total = this.toppings_total || 0;
		return json;
	},


	deleteLine(ev){
		let order = this.get_order();
		let orderline = this.props.line;
		let toppings = orderline.get_line_topping_ids();
		let y = jQuery.grep(toppings, function(value) {
		  return value != ev.detail.id;
		});
		orderline.set_line_topping_ids(y);
		let details  = orderline.getToppingDetails();
		let ltotal = ev.detail.total;
		orderline.price_type = "manual";
		orderline.set_unit_price(orderline.price - ltotal);
		orderline.price_manually_set = true;
	},


	get_toppingsData(){
		let order = this.pos.get_order();
		let line = this;
		let data = line.getToppingDetails();
		return data;
	},




	getToppingDetails(){
		let self = this;
		let topping_ids = this.line_topping_ids;
		let prod_list = [];
		let prod_dict = {};
		let t_total = 0;
		topping_ids.forEach(function (prod) {
			let product = self.pos.db.get_product_by_id(prod);
			if(product){
				t_total += product.lst_price;
				if(prod in prod_dict){
					let old_qty = prod_dict[prod]['qty'] + 1;

					prod_dict[prod] = {
						'id' : product.id,
						'name' : product.display_name,
						'uom' : product.uom_id[1],
						'qty' : old_qty,
						'rate' : product.lst_price,
						'total' : product.lst_price * old_qty,
					};
				}else{
					prod_dict[prod] = {
						'id' : product.id,
						'name' : product.display_name,
						'uom' : product.uom_id[1],
						'qty' : 1,
						'rate' : product.lst_price,
						'total' : product.lst_price ,
					};
				}
			}
			
		}); 
		self.set_toppings_total(t_total);
		prod_list = $.map(prod_dict, function(value, key) { return value });
		this.toppingdata = prod_list;
		return prod_list;
	}
});

