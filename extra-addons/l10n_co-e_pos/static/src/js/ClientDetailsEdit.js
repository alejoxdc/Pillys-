odoo.define('l10n_co-e_pos.ClientDetailsEdit', function(require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');
    const ClientDetailsEdit = require('point_of_sale.ClientDetailsEdit');

    const JClientDetailsEdit = (ClientDetailsEdit) =>
        class extends ClientDetailsEdit {
            constructor() {
                super(...arguments);
                this.intFields.push(
                    'l10n_latam_identification_type_id',
                    'tribute_id',
                    'fiscal_responsability_ids',
                    'city_id',
                );
                const partner = this.props.partner;
                this.changes = Object.assign({}, this.changes,
                    {
                        vat: partner.vat,
                        company_type: partner.company_type,
                        city: partner.city,
                        l10n_latam_identification_type_id: partner.l10n_latam_identification_type_id && partner.l10n_latam_identification_type_id[0],
                        tribute_id: partner.tribute_id && partner.tribute_id[0],
                        //fiscal_responsability_ids: partner.fiscal_responsability_ids && partner.fiscal_responsability_ids[0],
                        city_id: partner.city_id && partner.city_id[0],
                    }
                );
            }
        };

    Registries.Component.extend(ClientDetailsEdit, JClientDetailsEdit);

    return ClientDetailsEdit;
});