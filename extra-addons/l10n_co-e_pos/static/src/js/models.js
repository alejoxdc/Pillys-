odoo.define('l10n_co-e_pos.models', function (require) {
    "use strict";

    const { Context } = owl;
    const PosDB = require('point_of_sale.DB');
    const core = require('web.core');
    const exports = require('point_of_sale.models');
    const OrderSuper = exports.Order;
    const _t = core._t;
    var Models = require("point_of_sale.models");
    var rpc = require('web.rpc');

    Models.PosModel = Models.PosModel.extend({
        push_and_invoice_order: function (order) {
            var self = this;
            return new Promise((resolve, reject) => {
                if (!order.get_client()) {
                    reject({ code: 400, message: 'Missing Customer', data: {} });
                } else {
                    var order_id = self.db.add_order(order.export_as_JSON());
                    self.flush_mutex.exec(async () => {
                        try {
                            const server_ids = await self._flush_orders([self.db.get_order(order_id)], {
                                timeout: 30000,
                                to_invoice: true,
                            });
                            if (server_ids.length) {
                                if (!self.config.stop_invoice_print) {
                                    const [orderWithInvoice] = await self.rpc({
                                        method: 'read',
                                        model: 'pos.order',
                                        args: [server_ids, ['account_move']],
                                        kwargs: { load: false },
                                    });

                                    await self
                                        .do_action('account.account_invoices', {
                                            additional_context: {
                                                active_ids: [orderWithInvoice.account_move],
                                            },
                                        })
                                        .catch(() => {
                                            reject({ code: 401, message: 'Backend Invoice', data: { order: order } });
                                        });
                                }
                            } else {
                                reject({ code: 401, message: 'Backend Invoice', data: { order: order } });
                            }
                            resolve(server_ids);
                        } catch (error) {
                            reject(error);
                        }
                    });
                }
            });
        },
    });

    const models = exports.PosModel.prototype.models;

    models.push(
        {
            model: 'dian.tributes',
            fields: ['id', 'name'],
            loaded: function (self, dian_tributes) {
                self.dian_tributes = dian_tributes;
            }
        },
        {
            model: 'dian.fiscal.responsability',
            fields: ['id', 'name'],
            loaded: function (self, dian_fiscal_responsability) {
                self.dian_fiscal_responsability = dian_fiscal_responsability;
            }
        },
        {
            model: 'res.city',
            fields: ['id', 'name', 'state_id'],
            loaded: function (self, res_city2) {
                self.res_city2 = res_city2;
            }
        },
        {
            model: 'l10n_latam.identification.type',
            fields: ['id', 'name', 'l10n_co_document_code'],
            loaded: function (self, l10n_latam_identification_types) {
                self.l10n_latam_identification_types = l10n_latam_identification_types;
            }
        }
    );

    exports.load_fields("res.partner", [
        "company_type",
        "l10n_latam_identification_type_id",
        "tribute_id",
        //"fiscal_responsability_ids",
        "city_id",
        "email_invoice_electronic",]);

    exports.load_fields("res.company", ["state_id", "city"]);

    var _super_order = Models.Order.prototype;
    Models.Order = Models.Order.extend({
        initialize: function (attributes, options) {
            _super_order.initialize.apply(this, arguments);
            this.to_electronic_invoice = false;

            this.dian_number = this.dian_number || false;
            this.dian_cufe = this.dian_cufe || false;
            this.dian_co_qr_data = this.dian_co_qr_data || false;
            this.dian_ei_is_valid = this.dian_ei_is_valid || false;
            this.dian_state_dian_document = this.dian_state_dian_document || false;
            this.dian_resolution_number = this.dian_resolution_number || false;
            this.dian_resolution_date = this.dian_resolution_date || false;
            this.dian_resolution_date_to = this.dian_resolution_date_to || false;
            this.dian_resolution_number_to = this.dian_resolution_number_to || false;
            this.dian_resolution_number_from = this.dian_resolution_number_from || false;
            this.dian_invoice_date = this.dian_invoice_date || false;
            this.dian_invoice_date_due = this.dian_invoice_date_due || false;
            this.dian_invoice_origin = this.dian_invoice_origin || false;
            this.dian_ref = this.dian_ref || false;
            this.dian_formatedNit = this.dian_formatedNit || false;
            this.dian_company_idname = this.dian_company_idname || false;
            this.pos_number = this.pos_number || false;
            this.save_to_db();
        },

        init_from_JSON: function (json) {
            _super_order.init_from_JSON.apply(this, arguments);
            this.to_electronic_invoice = false;
            this.set_dian_number(json.dian_number || false);
            this.set_dian_cufe(json.dian_cufe || false);
            this.set_dian_co_qr_data(json.dian_co_qr_data || false);
            this.set_dian_ei_is_valid(json.dian_ei_is_valid || false);
            this.set_dian_state_dian_document(json.dian_state_dian_document || false);
            this.set_dian_resolution_number(json.dian_resolution_number || false);
            this.set_dian_resolution_date(json.dian_resolution_date || false);
            this.set_dian_resolution_date_to(json.dian_resolution_date_to || false);
            this.set_dian_resolution_number_to(json.dian_resolution_number_to || false);
            this.set_dian_resolution_number_from(json.dian_resolution_number_from || false);
            this.set_dian_invoice_date(json.dian_invoice_date || false);
            this.set_dian_invoice_date_due(json.dian_invoice_date_due || false);
            this.set_dian_invoice_origin(json.dian_invoice_origin || false);
            this.set_dian_ref(json.dian_ref || false);
            this.set_dian_formatedNit(json.dian_formatedNit || false);
            this.set_dian_company_idname(json.dian_company_idname || false);
            this.set_pos_number(json.pos_number || false);
            this.set_to_invoice(Boolean(json.dian_number) || false);
        },
        export_as_JSON: function () {
            const json = _super_order.export_as_JSON.apply(this, arguments);
            json.to_electronic_invoice = this.to_electronic_invoice ? this.to_electronic_invoice : false;
            json.dian_number = this.get_dian_number();
            json.dian_cufe = this.get_dian_cufe();
            json.dian_co_qr_data = this.get_dian_co_qr_data();
            json.dian_ei_is_valid = this.get_dian_ei_is_valid();
            json.dian_state_dian_document = this.get_dian_state_dian_document();
            json.dian_resolution_number = this.get_dian_resolution_number();
            json.dian_resolution_date = this.get_dian_resolution_date();
            json.dian_resolution_date_to = this.get_dian_resolution_date_to();
            json.dian_resolution_number_to = this.get_dian_resolution_number_to();
            json.dian_resolution_number_from = this.get_dian_resolution_number_from();
            json.dian_invoice_date = this.get_dian_invoice_date();
            json.dian_invoice_date_due = this.get_dian_invoice_date_due();
            json.dian_invoice_origin = this.get_dian_invoice_origin();
            json.dian_ref = this.get_dian_ref();
            json.dian_formatedNit = this.get_dian_formatedNit();
            json.dian_company_idname = this.get_dian_company_idname();
            json.pos_number = this.get_pos_number();
            return json;
        },
        export_for_printing: function () {
            const receipt = _super_order.export_for_printing.apply(this, arguments);
            receipt.dian_number = this.get_dian_number();
            receipt.dian_cufe = this.get_dian_cufe();
            receipt.dian_co_qr_data = this.get_dian_co_qr_data();
            receipt.dian_ei_is_valid = this.get_dian_ei_is_valid();
            receipt.dian_state_dian_document = this.get_dian_state_dian_document();
            receipt.dian_resolution_number = this.get_dian_resolution_number();
            receipt.dian_resolution_date = this.get_dian_resolution_date();
            receipt.dian_resolution_date_to = this.get_dian_resolution_date_to();
            receipt.dian_resolution_number_to = this.get_dian_resolution_number_to();
            receipt.dian_resolution_number_from = this.get_dian_resolution_number_from();
            receipt.dian_invoice_date = this.get_dian_invoice_date();
            receipt.dian_invoice_date_due = this.get_dian_invoice_date_due();
            receipt.dian_invoice_origin = this.get_dian_invoice_origin();
            receipt.dian_ref = this.get_dian_ref();
            receipt.dian_formatedNit = this.get_dian_formatedNit();
            receipt.dian_company_idname = this.get_dian_company_idname();
            receipt.pos_number = this.get_pos_number()
            receipt.qr_code = this.get_qr_code(this.get_dian_co_qr_data());
            receipt.to_invoice = this.is_to_invoice();
            return receipt;
        },
        get_qr_code(qr_data) {
            if (qr_data) {
                  const codeWriter = new window.ZXing.BrowserQRCodeSvgWriter();
                  let qr_code_svg = new XMLSerializer().serializeToString(codeWriter.write(qr_data, 150, 150));
                  return "data:image/svg+xml;base64,"+ window.btoa(qr_code_svg);
              } else {
                  return false;
              }
        },
        set_to_electronic_invoice: function (to_electronic_invoice) {
            this.assert_editable();
            this.to_electronic_invoice = to_electronic_invoice;
        },
        is_to_electronic_invoice: function () {
            return this.to_electronic_invoice;
        },
        set_pos_number(pos_number) {
            this.pos_number = pos_number;
        },
        get_pos_number() {
            return this.pos_number;
        },

        get_dian_number() {
            return this.dian_number;
        },
        set_dian_number(dian_number) {
            this.dian_number = dian_number;
        },
        get_dian_cufe() {
            return this.dian_cufe;
        },
        set_dian_cufe(dian_cufe) {
            this.dian_cufe = dian_cufe;
        },
        get_dian_co_qr_data() {
            return this.dian_co_qr_data;
        },
        set_dian_co_qr_data(dian_co_qr_data) {
            this.dian_co_qr_data = dian_co_qr_data;
        },
        get_dian_ei_is_valid() {
            return this.dian_ei_is_valid;
        },
        set_dian_ei_is_valid(dian_ei_is_valid) {
            this.dian_ei_is_valid = dian_ei_is_valid;
        },
        get_dian_state_dian_document() {
            return this.dian_state_dian_document;
        },
        set_dian_state_dian_document(dian_state_dian_document) {
            this.dian_state_dian_document = dian_state_dian_document;
        },
        get_dian_resolution_number() {
            return this.dian_resolution_number;
        },
        set_dian_resolution_number(dian_resolution_number) {
            this.dian_resolution_number = dian_resolution_number;
        },
        get_dian_resolution_date() {
            return this.dian_resolution_date;
        },
        set_dian_resolution_date(dian_resolution_date) {
            this.dian_resolution_date = dian_resolution_date;
        },
        get_dian_resolution_date_to() {
            return this.dian_resolution_date_to;
        },
        set_dian_resolution_date_to(dian_resolution_date_to) {
            this.dian_resolution_date_to = dian_resolution_date_to;
        },
        get_dian_resolution_number_to() {
            return this.dian_resolution_number_to;
        },
        set_dian_resolution_number_to(dian_resolution_number_to) {
            this.dian_resolution_number_to = dian_resolution_number_to;
        },
        get_dian_resolution_number_from() {
            return this.dian_resolution_number_from;
        },
        set_dian_resolution_number_from(dian_resolution_number_from) {
            this.dian_resolution_number_from = dian_resolution_number_from;
        },
        get_dian_invoice_date() {
            return this.dian_invoice_date;
        },
        set_dian_invoice_date(dian_invoice_date) {
            this.dian_invoice_date = dian_invoice_date;
        },
        get_dian_invoice_date_due() {
            return this.dian_invoice_date_due;
        },
        set_dian_invoice_date_due(dian_invoice_date_due) {
            this.dian_invoice_date_due = dian_invoice_date_due;
        },
        get_dian_invoice_origin() {
            return this.dian_invoice_origin;
        },
        set_dian_invoice_origin(dian_invoice_origin) {
            this.dian_invoice_origin = dian_invoice_origin;
        },
        get_dian_ref() {
            return this.dian_ref;
        },
        set_dian_ref(dian_ref) {
            this.dian_ref = dian_ref;
        },
        get_dian_formatedNit() {
            return this.dian_formatedNit;
        },
        set_dian_formatedNit(dian_formatedNit) {
            this.dian_formatedNit = dian_formatedNit;
        },
        get_dian_company_idname() {
            return this.dian_company_idname;
        },
        set_dian_company_idname(dian_company_idname) {
            this.dian_company_idname = dian_company_idname;
        },
    });
});