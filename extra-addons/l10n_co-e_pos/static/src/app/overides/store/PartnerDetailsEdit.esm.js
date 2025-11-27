/** @odoo-module **/
import {ErrorPopup} from "@point_of_sale/app/errors/popups/error_popup";
import {PartnerDetailsEdit} from "@point_of_sale/app/screens/partner_list/partner_editor/partner_editor";
import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";

patch(PartnerDetailsEdit.prototype, {
    setup() {
        super.setup(...arguments);
        this.popup = useService("popup");
        this.partner_names_order = this.pos.config.partner_names_order;
        this.changes.is_company = this.props.partner.is_company;
        this.changes.firs_name = this.props.partner.firs_name;
        this.changes.first_lastname = this.props.partner.first_lastname;
        this.changes.category_id = this.props.partner.category_id && this.props.partner.category_id[0];
        this.changes.tribute_id = this.props.partner.tribute_id && this.props.partner.tribute_id[0];
        this.changes.fiscal_responsability_ids = this.props.partner.fiscal_responsability_ids && this.props.partner.fiscal_responsability_ids[0];
        this.intFields.push("city_id", "l10n_latam_identification_type_id","tribute_id");
        this.changes.city_id = this.props.partner.city_id && this.props.partner.city_id[0];
        this.changes.l10n_latam_identification_type_id =
            this.props.partner.l10n_latam_identification_type_id &&
            this.props.partner.l10n_latam_identification_type_id[0];
    },
    get isCompanyIcon() {
        if (this.changes.is_company) {
            return "fa-building";
        }
        return "fa-user";
    },
    toggleIsCompany() {
        this.changes.is_company = !this.changes.is_company;
    },
    checkPartnerPersonName() {
        /* We add this hook in order to check second last name later */
        return !this.changes.firs_name && !this.changes.first_lastname && !this.changes.city_id && !this.changes.vat;
    },
    saveChanges() {
        if (this.changes.is_company) {
            this.changes.first_lastname = this.changes.firs_name = undefined;
        } else {
            if (this.checkPartnerPersonName()) {
                return this.popup.add(ErrorPopup, {
                    title: _t("Información faltante"),
                    body: _t("Se requiere el nombre o apellido o Ciudad o NIT/CC del cliente"),
                });
            }
            this.changes.name = this._updatePartnerName(
                this.changes.firs_name,
                this._getLastName(this.changes)
            );
        }

        if (
            (!this.props.partner.category_id && !this.changes.category_id) ||
            this.changes.category_id === ""
        ) {
            this.changes.category_id = false
        } else {
            this.changes.category_id = [parseInt(this.changes.category_id)];
        }

        if (
            (!this.props.partner.tribute_id && !this.changes.tribute_id) ||
            this.changes.tribute_id === ""
        ) {
            this.changes.tribute_id = false
        } else {
            this.changes.tribute_id = this.changes.tribute_id;
        }


        if (
            (!this.props.partner.fiscal_responsability_ids && !this.changes.fiscal_responsability_ids) ||
            this.changes.fiscal_responsability_ids === ""
        ) {
            this.changes.fiscal_responsability_ids = false
        } else {
            this.changes.fiscal_responsability_ids = [parseInt(this.changes.fiscal_responsability_ids)];
        }
        super.saveChanges();
    },
    _getLastName(changes) {
        return changes.first_lastname;
    },
    _updatePartnerName(firs_name, first_lastname) {
        let name = null;
        if (!first_lastname) {
            return firs_name;
        }
        if (!firs_name) {
            return first_lastname;
        }
        if (this.partner_names_order === "last_first_comma") {
            name = first_lastname + ", " + firs_name;
        } else if (this.partner_names_order === "first_last") {
            name = firs_name + " " + first_lastname;
        } else {
            name = first_lastname + " " + firs_name;
        }
        return name.trim();
    },
});
