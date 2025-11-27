odoo.define('l10n_co-e_pos.ClientListScreen', function(require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');
    const ClientListScreen = require('point_of_sale.ClientListScreen');

    const JClientListScreen = (ClientListScreen) =>
        class extends ClientListScreen {
            constructor() {
                super(...arguments);
                this.state.editModeProps.partner = Object.assign({}, this.state.editModeProps.partner,
                    {
                        vat: '222222222222',
                        company_type: 'person',
                        city: this.env.pos.company.city,
                        l10n_latam_identification_type_id: [this.env.pos.l10n_latam_identification_types.find(o => o.l10n_co_document_code=='national_citizen_id')['id']],
                        tribute_id: [4],
                        state: this.env.pos.company.state_id,
                        city_id: this.env.pos.company.city_id,
                    }
                );
            }
        };

    Registries.Component.extend(ClientListScreen, JClientListScreen);

    return ClientListScreen;
});