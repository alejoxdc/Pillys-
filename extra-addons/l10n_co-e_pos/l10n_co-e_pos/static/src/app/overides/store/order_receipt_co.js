/** @odoo-module **/

import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";

Orderline.props = {
    class: { type: Object, optional: true },
    line: {
        type: Object,
        shape: {
            productName: String,
            price: String,
            qty: String,
            totalco: String,
            quantity: String,
            unit: { type: String, optional: true },
            unitPrice: String,
            discount: { type: String, optional: true },
            is_reward_line: { type: Boolean, optional: true },
            default_code: { type: String, optional: true },
            comboParent: { type: String, optional: true },
            oldUnitPrice: { type: String, optional: true },
            customerNote: { type: String, optional: true },
            internalNote: { type: String, optional: true },
            attributes: { type: Array, optional: true },
            "*": true,
        },
    },
    slots: { type: Object, optional: true },
};

OrderReceipt.template="OrderReceiptCO";
