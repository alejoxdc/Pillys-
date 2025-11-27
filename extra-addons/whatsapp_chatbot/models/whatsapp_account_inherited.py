# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import mimetypes
import secrets
import string
from datetime import timedelta
from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.whatsapp_chatbot.tools.whatsapp_api import WhatsAppApi
from odoo.addons.whatsapp.tools.whatsapp_exception import WhatsAppError
from odoo.tools import plaintext2html

_logger = logging.getLogger(__name__)

class WhatsappAccountInherited(models.Model):
    
    _inherit = "whatsapp.account"

    def _process_messages(self, value):
        _logger.info("Processing messages 2")
        """
            This method is used for processing messages with the values received via webhook.
            If any whatsapp message template has been sent from this account then it will find the active channel or
            create new channel with last template message sent to that number and post message in that channel.
            And if channel is not found then it will create new channel with notify user set in account and post message.
            Supported Messages
            => Text Message
            => Attachment Message with caption
            => Location Message
            => Contact Message
            => Message Reactions
        """
        if 'messages' not in value and value.get('whatsapp_business_api_data', {}).get('messages'):
            value = value['whatsapp_business_api_data']

        wa_api = WhatsAppApi(self)

        for messages in value.get('messages', []):
            parent_id = False
            channel = False
            sender_name = value.get('contacts', [{}])[0].get('profile', {}).get('name')
            sender_mobile = messages['from']
            message_type = messages['type']
            if 'context' in messages and messages['context'].get('id'):
                parent_whatsapp_message = self.env['whatsapp.message'].sudo().search([('msg_uid', '=', messages['context']['id'])])
                if parent_whatsapp_message:
                    parent_id = parent_whatsapp_message.mail_message_id
                if parent_id:
                    channel = self.env['discuss.channel'].sudo().search([('message_ids', 'in', parent_id.id)], limit=1)

            if not channel:
                channel = self._find_active_channel(sender_mobile, sender_name=sender_name, create_if_not_found=True)
            kwargs = {
                'message_type': 'whatsapp_message',
                'author_id': channel.whatsapp_partner_id.id,
                'subtype_xmlid': 'mail.mt_comment',
                'parent_id': parent_id.id if parent_id else None
            }
            if message_type == 'text':
                kwargs['body'] = plaintext2html(messages['text']['body'])
            elif message_type == 'button':
                kwargs['body'] = messages['button']['text']
            elif message_type in ('document', 'image', 'audio', 'video', 'sticker'):
                _logger.info(messages)
                filename = messages[message_type].get('filename')
                mime_type = messages[message_type].get('mime_type')
                caption = messages[message_type].get('caption')
                datas = wa_api._get_whatsapp_document(messages[message_type]['id'])
                if not filename:
                    extension = mimetypes.guess_extension(mime_type) or '.opus'
                    filename = message_type + extension
                kwargs['attachments'] = [(filename, datas)]
                if caption:
                    kwargs['body'] = plaintext2html(caption)
            elif message_type == 'location':
                url = Markup("https://maps.google.com/maps?q={latitude},{longitude}").format(
                    latitude=messages['location']['latitude'], longitude=messages['location']['longitude'])
                body = Markup('<a target="_blank" href="{url}"> <i class="fa fa-map-marker"/> {location_string} </a>').format(
                    url=url, location_string=_("Location"))
                if messages['location'].get('name'):
                    body += Markup("<br/>{location_name}").format(location_name=messages['location']['name'])
                if messages['location'].get('address'):
                    body += Markup("<br/>{location_address}").format(location_name=messages['location']['address'])
                kwargs['body'] = body
            elif message_type == 'contacts':
                body = ""
                for contact in messages['contacts']:
                    body += Markup("<i class='fa fa-address-book'/> {contact_name} <br/>").format(
                        contact_name=contact.get('name', {}).get('formatted_name', ''))
                    for phone in contact.get('phones'):
                        body += Markup("{phone_type}: {phone_number}<br/>").format(
                            phone_type=phone.get('type'), phone_number=phone.get('phone'))
                kwargs['body'] = body
            elif message_type == 'reaction':
                msg_uid = messages['reaction'].get('message_id')
                whatsapp_message = self.env['whatsapp.message'].sudo().search([('msg_uid', '=', msg_uid)])
                if whatsapp_message:
                    partner_id = channel.whatsapp_partner_id
                    emoji = messages['reaction'].get('emoji')
                    whatsapp_message.mail_message_id._post_whatsapp_reaction(reaction_content=emoji, partner_id=partner_id)
                    continue
            else:
                _logger.warning("Unsupported whatsapp message type: %s", messages)
                continue
            channel.message_post(whatsapp_inbound_msg_uid=messages['id'], **kwargs)