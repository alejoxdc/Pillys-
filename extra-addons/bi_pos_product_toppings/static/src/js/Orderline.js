/** @odoo-module */

import { Orderline } from "@pos_preparation_display/app/components/orderline/orderline";
import { patch } from "@web/core/utils/patch";


patch(Orderline.prototype, {
    setup() {
        super.setup(...arguments);
    },

    get toppingData() {
        var self = this;
        var prod_name_list = []

        if(this.preparationDisplay){
            var all_products = this.preparationDisplay.all_pro
            var line_topping_ids = this.preparationDisplay.line_topping_ids
            for (const key in line_topping_ids) {
                if(key == this.props.orderline.id){
                    for(let n=0; n < all_products.length; n++){
                        if (line_topping_ids[key].includes(all_products[n]['id'])){
                            prod_name_list.push(all_products[n]['display_name'])
                        }
                    }
                }
            }
            if(prod_name_list.length > 0){
                return prod_name_list;
            }else{
                return false;
            }
        }
    }

});
