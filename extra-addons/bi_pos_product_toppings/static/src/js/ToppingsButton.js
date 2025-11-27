/** @odoo-module */

import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { Component } from "@odoo/owl";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { ToppingPopup } from "@bi_pos_product_toppings/js/ToppingPopup";
import { _t } from "@web/core/l10n/translation";

export class ToppingsButton extends Component {
    static template = "bi_pos_product_toppings.ToppingsButton";

    setup() {
    	super.setup();
        this.pos = usePos();
    }

    async onClick() {
		let self = this;
		var order = this.pos.get_order();
		var orderlines = order.get_orderlines();
		if (orderlines.length === 0) {
			this.pos.popup.add(ErrorPopup,{
				'title': _t('Empty Order'),
				'body': _t('There must be at least one product in your order before applying order type.'),
			});
			return;
		}
		else{
			var prod_list = [];
			let selected_orderline = order.get_selected_orderline();					
			if(selected_orderline && selected_orderline.product && selected_orderline.product.topping_ids.length > 0){
				let arr = selected_orderline.product.topping_ids;
				let aa = arr.filter((item,index) => arr.indexOf(item) === index);
				aa.forEach(function (prod) {
					var top_prod = self.pos.db.get_product_by_id(prod);
					if (top_prod){
						prod_list.push(top_prod);
					}
                });
			}
            
            this.pos.popup.add(ToppingPopup, {'toppings':prod_list});
		}
	}

    
}

ProductScreen.addControlButton({
    component: ToppingsButton,
    position: ["before", "SetFiscalPositionButton"],
    condition: function () {
        return this.pos.config.activate_toppings;
    },
});
