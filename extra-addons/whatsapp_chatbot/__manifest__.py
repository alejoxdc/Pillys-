{
    'name': 'Odoo Whatsapp Chatbot',
    'version': '1.2',
    'category': 'Chat',
    'summary': 'Module to create automated conversations on Whatsapp',
    'sequence': 10,
    'license': 'LGPL-3',
    'author': 'Your Name',
    'website': 'https://www.yourwebsite.com',
    'depends': ['base', 'resource', 'mail', 'whatsapp', 'crm', 'utm', 'sale_management', 'facebook_campaign_identification'],
    'data': [
        'views/chatbot_view.xml',
        'views/chatbot_flow_view.xml',
        'views/message_warning_view.xml',
        'views/whatsapp_template_views.xml',
        'views/whatsapp_quick_response_views.xml',
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
    ],
    'demo': [],
    'assets': {
        'web.assets_backend': [
            'whatsapp_chatbot/static/src/discuss/core/common/**/*',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'description': """
    This module allows to create automated conversations on Whatsapp using a chatbot.
    It uses the webhook system of the Whatsapp API integration to catch the received messages and message updates.
    The user can set the communication flow by ordered messages of various kinds such as text, templates, templates with buttons and Odoo server actions.
    """,
}