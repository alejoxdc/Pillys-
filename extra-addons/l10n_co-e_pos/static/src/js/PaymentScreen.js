odoo.define('l10n_co-e_pos.PaymentScreen', function (require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');
    const PaymentScreen = require('point_of_sale.PaymentScreen');

    const JPaymentScreen = (PaymentScreen) =>
        class extends PaymentScreen {
            constructor() {
                super(...arguments);
            }
            toggleIsToElectronicInvoice() {
                this.currentOrder.set_to_electronic_invoice(!this.currentOrder.is_to_electronic_invoice());
                this.render();
            }
            async _postPushOrderResolve(order, order_server_ids) {
                try {
                    if (order.is_to_invoice()) {
                        const result = await this.rpc({
                            model: 'pos.order',
                            method: 'get_invoice',
                            args: [order_server_ids],
                        });
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
                        // order.set_invoice(result || null);
                    }
                } finally {
                    return super._postPushOrderResolve(...arguments);
                }
            }
            async validateOrder(isForceValidate) {
                if (this.currentOrder) {
                    if (this.refunded_order_ids && this.refunded_order_ids.length > 0) {
                        // Verificar que todas las facturas asociadas tengan el campo state_dian_document igual a 'exito'
                        const allInvoicesSuccessful = this.refunded_order_ids.every(invoice => {
                            return invoice.account_move && invoice.account_move.state_dian_document === 'exito';
                        });

                        if (allInvoicesSuccessful) {
                            // Todas las facturas están en estado 'exito', proceder con la lógica de la nota de crédito electrónica
                            // ...
                        } else {
                            // Al menos una factura no está en estado 'exito', mostrar un aviso y retornar false
                            this.showPopup("ErrorPopup", {
                                title: this.env._t("ALERT"),
                                body: this.env._t("No se puede crear la nota de crédito electrónica. Al menos una factura no está en estado 'exito'."),
                            });
                            return false;
                        }
                    }
                }
                return await super.validateOrder(...arguments);
            }
        };

    Registries.Component.extend(PaymentScreen, JPaymentScreen);

    return PaymentScreen;
});