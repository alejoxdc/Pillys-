# -*- coding: utf-8 -*-
#
{
    'name': 'Facturación electrónica POS para Colombia',
    'description': "Free POS electronic invoice for Colombia",
    'author': 'Lavish',
    'license': 'AGPL-3',
    'category': 'Point of Sale',
    'version': '15.0',
    'depends': [
        'point_of_sale',
        'l10n_co_e-invoice',
    ],
    'data': [
        'views/pos_config_view.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_co-e_pos/static/src/css/pos.css',
            'l10n_co-e_pos/static/src/css/PartnerDetailsEdit.scss',
            'l10n_co-e_pos/static/src/app/overides/**/*',
            'l10n_co-e_pos/static/src/xml/**/*',
        ],
    },
    'installable': True,
    'auto_install': False,
}
