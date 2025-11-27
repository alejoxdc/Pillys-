/** @odoo-module **/

// import { _t } from "@web/core/l10n/translation";
// import { parseFloat } from "@web/views/fields/parsers";
// import { registry } from "@web/core/registry";
// import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
// import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";
// import { usePos } from "@point_of_sale/app/store/pos_hook";
// import { useService } from "@web/core/utils/hooks";
// import { Component, useRef, onMounted } from "@odoo/owl";
// import { TipScreen   } from "@pos_restaurant/app/tip_screen/tip_screen";
// import { patch } from "@web/core/utils/patch";

// patch(TipScreen.prototype, {
//     setup() {
//         this.pos = usePos();
//         this.posReceiptContainer = useRef("pos-receipt-container");
//         this.popup = useService("popup");
//         this.orm = useService("orm");
//         this.printer = useService("printer");
//         this.state = this.currentOrder.uiState.TipScreen;
//         this._totalAmount = this.currentOrder.get_total_with_tax();

//         onMounted(async () => {
//             await this.printTipReceipt();
//         });
//     },

//     get totalAmount() {
//         return this._totalAmount;
//     },
//     get currentOrder() {
//         return this.pos.get_order();
//     },
//     get percentageTips() {
//         return [
//            // { percentage: "5%", amount: 0.05 * this.totalAmount },
//             { percentage: "10%", amount: 0.10 * this.totalAmount },
//            //{ percentage: "15%", amount: 0.15 * this.totalAmount },
//         ];
//     }

// });
