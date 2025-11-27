/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { _t } from "@web/core/l10n/translation";

patch(PaymentScreen.prototype, {


    async _postPushOrderResolve(order, order_server_ids) {
        try {
            if (order.is_to_invoice()) {
                // const result = await this.orm.call({
                //     model: 'pos.order',
                //     method: 'get_invoice',
                //     args: [order_server_ids],
                // });
                const result = await this.orm.call('pos.order', 'get_invoice', order_server_ids);
                order.set_dian_number(result.number);
                order.set_dian_cufe(result.cufe);
                order.set_dian_co_qr_data(result.co_qr_data);
                order.set_dian_ei_is_valid(result.ei_is_valid);
                order.set_dian_state_dian_document(result.state_dian_document);
                order.set_dian_resolution_number(result.resolution_number);
                order.set_dian_resolution_date(result.resolution_date);
                order.set_dian_resolution_date_to(result.resolution_date_to);
                order.set_dian_resolution_number_to(result.resolution_number_to);
                order.set_dian_resolution_number_from(result.resolution_number_from);
                order.set_dian_invoice_date(result.invoice_date);
                order.set_dian_invoice_date_due(result.invoice_date_due);
                order.set_dian_invoice_origin(result.invoice_origin);
                order.set_dian_ref(result.ref);
                order.set_dian_formatedNit(result.formatedNit);
                order.set_dian_company_idname(result.company_idname);
                order.set_pos_number(result.pos_number);
            }else {
                const result = await this.orm.call('pos.order', 'get_invoice', order_server_ids);
                order.set_pos_number(result.pos_number);
            }
        } catch (error) {
            console.error(error);
            return [];
            // FIXME this doesn't seem correct but is equivalent to return in finally which we had before.
        }
        return super._postPushOrderResolve(...arguments);
    },
    async _isOrderValid(isForceValidate) {
        const result = await super._isOrderValid(...arguments);
        if (this.pos.isColombiaCompany()) {
            if (!result) {
                return false;
            }
            const mandatoryFacturaFields = [
                "email",
                "city_id",
                "street",
                "l10n_latam_identification_type_id",
                "vat",
                "fiscal_responsability_ids",
                "tribute_id",
            ];
            const missingFields = [];
            const partner = this.currentOrder.get_partner();
            if (this.currentOrder.is_to_invoice() || this.currentOrder._isRefundOrder()) {
                for (const field of mandatoryFacturaFields) {
                    if (!partner[field]) {
                        missingFields.push(field);
                    }
                }
            }
            if (missingFields.length > 0) {
                this.notification.add(_t("Complete los campos que faltan para continuar.", 5000)
                );
                this.selectPartner(true, missingFields);
                return false;
            }
            return true;
        }
        return result;
    },
    shouldDownloadInvoice() {
        const res = super.shouldDownloadInvoice()
        if (this.pos.isColombiaCompany()) {
            return false
        }
        return res
    },
});
