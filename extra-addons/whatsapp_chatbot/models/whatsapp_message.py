import logging
from odoo import models
import markupsafe
from markupsafe import Markup
from bs4 import BeautifulSoup
from odoo.tools.mail import html_sanitize
import re

from datetime import timedelta

from odoo import models, fields, api, _, Command
from odoo.addons.phone_validation.tools import phone_validation
from odoo.addons.whatsapp.tools import phone_validation as wa_phone_validation
from odoo.addons.whatsapp.tools.retryable_codes import WHATSAPP_RETRYABLE_ERROR_CODES
from odoo.addons.whatsapp.tools.whatsapp_api import WhatsAppApi
from odoo.addons.whatsapp.tools.whatsapp_exception import WhatsAppError
from odoo.exceptions import ValidationError, UserError
from odoo.tools import groupby, html2plaintext

_logger = logging.getLogger(__name__)

class WhatsAppMessage(models.Model):
    _inherit = "whatsapp.message"

    def _post_message_in_active_channel(self):
        super()._post_message_in_active_channel()
        if not self.wa_template_id:
            return
        channel = self.wa_account_id._find_active_channel(self.mobile_number_formatted)
        if not channel:
            return

        formatted_body = self.wa_template_id._get_formatted_body(demo_fallback=True)
        reorganized_html = self._reorganize_html(formatted_body, self.wa_template_id)
        
        channel.sudo().message_post(
            message_type='notification',
            body=Markup('<div>{message_body}</div>').format(
                message_body=reorganized_html,
            ),
        )
    
    def remove_tags(self, html, tags_to_remove):
        soup = BeautifulSoup(html, 'html.parser')

        for tag in tags_to_remove:
            for tag_to_remove in soup.find_all(tag):
                tag_to_remove.decompose()

        return str(soup)

    def sanitize_input(self, input_string):
        return input_string.encode('utf-8', 'ignore').decode('utf-8')

    def generate_html_container(self, message_tags, template=False):
        soup = BeautifulSoup("", 'html.parser')

        # Create the container
        container = soup.new_tag('div', style='border: 1px solid #25D366; border-radius: 5px; padding: 10px; margin: 10px; font-family: Arial, sans-serif; background-color: #FFF;')

        # Create the image
        img = soup.new_tag('img', src='/whatsapp_chatbot/static/img/whatsapp.svg', style='width: 20px; height: 20px; display: inline-block; vertical-align: middle;')

        # Create the span
        span = soup.new_tag('span', style='display: inline-block; vertical-align: middle; margin-left: 10px; color: #075E54; font-weight: bold;')
        span.string = template.name

        # Create the p
        p = soup.new_tag('div', style='border-radius: 5px; padding: 10px; background-color: #DCF8C6; color: #075E54; margin-top: 10px;')

        # Append the message tags to the p
        message = ' '.join(str(tag).rstrip() for tag in message_tags if str(tag) != '<br>')
        sanitized_message = self.sanitize_input(message)
        p.append(BeautifulSoup(sanitized_message, 'html.parser'))

        # Append the elements to the container
        container.append(img)
        container.append(span)
        container.append(p)

        emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
            u"\U00002702-\U000027B0"
            u"\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE)
    
        # Remove emojis from the text
        text_without_emojis = emoji_pattern.sub(r'', str(container))

        tags_to_remove = ['br']

        return self.remove_tags(text_without_emojis, tags_to_remove)

    def _reorganize_html(self, html, template=False):
        soup = BeautifulSoup(html, 'html.parser')

        # Create a new tag with some styles
        new_tag = soup.new_tag('div')

        # Move all the content into the new tag
        for tag in soup.find_all(True):
            new_tag.append(tag.extract())

        # Generate the beautiful container with the children of the new tag
        container = self.generate_html_container(new_tag.contents, template)

        # Return the container
        return html_sanitize(container)
    
    def html2plaintext_custom(self, html):
        # Replace <br> tags with newline characters
        html = re.sub(r'<br\s*/?>', '\n', html)
        # Remove all other HTML tags
        text = re.sub(r'<[^>]+>', '', html)
        return text

    def _send_message(self, with_commit=False):
        """ Prepare json data for sending messages, attachments and templates."""
        _logger.info("Sending messages2")
        # init api
        message_to_api = {}
        for account, messages in groupby(self, lambda msg: msg.wa_account_id):
            if not account:
                messages = self.env['whatsapp.message'].concat(*messages)
                messages.write({
                    'failure_type': 'unknown',
                    'failure_reason': 'Missing whatsapp account for message.',
                    'state': 'error',
                })
                self -= messages
                continue
            wa_api = WhatsAppApi(account)
            for message in messages:
                message_to_api[message] = wa_api

        for whatsapp_message in self:
            wa_api = message_to_api[whatsapp_message]
            # try to make changes with current user (notably due to ACLs), but limit
            # to internal users to avoid crash - rewrite me in master please
            if whatsapp_message.create_uid._is_internal():
                whatsapp_message = whatsapp_message.with_user(whatsapp_message.create_uid)
            if whatsapp_message.state != 'outgoing':
                _logger.info("Message state in %s state so it will not sent.", whatsapp_message.state)
                continue
            msg_uid = False
            try:
                parent_message_id = False
                body = whatsapp_message.body
                body = self.html2plaintext_custom(whatsapp_message.body)
                if isinstance(body, markupsafe.Markup):
                    # If Body is in html format so we need to remove html tags before sending message.
                    body = body.striptags()
                number = whatsapp_message.mobile_number_formatted
                if not number:
                    raise WhatsAppError(failure_type='phone_invalid')
                if self.env['phone.blacklist'].sudo().search([('number', 'ilike', number), ('active', '=', True)]):
                    raise WhatsAppError(failure_type='blacklisted')

                # based on template
                if whatsapp_message.wa_template_id:
                    message_type = 'template'
                    if whatsapp_message.wa_template_id.status != 'approved' or whatsapp_message.wa_template_id.quality == 'red':
                        raise WhatsAppError(failure_type='template')
                    whatsapp_message.message_type = 'outbound'
                    if whatsapp_message.mail_message_id.model != whatsapp_message.wa_template_id.model:
                        raise WhatsAppError(failure_type='template')

                    RecordModel = self.env[whatsapp_message.mail_message_id.model].with_user(whatsapp_message.create_uid)
                    from_record = RecordModel.browse(whatsapp_message.mail_message_id.res_id)

                    # if retrying message then we need to unlink previous attachment
                    # in case of header with report in order to generate it again
                    if whatsapp_message.wa_template_id.report_id and whatsapp_message.wa_template_id.header_type == 'document' and whatsapp_message.mail_message_id.attachment_ids:
                        whatsapp_message.mail_message_id.attachment_ids.unlink()

                    # generate sending values, components and attachments
                    send_vals, attachment = whatsapp_message.wa_template_id._get_send_template_vals(
                        record=from_record,
                        free_text_json=whatsapp_message.free_text_json,
                        attachment=whatsapp_message.mail_message_id.attachment_ids,
                    )
                    if attachment and attachment not in whatsapp_message.mail_message_id.attachment_ids:
                        whatsapp_message.mail_message_id.attachment_ids = [(4, attachment.id)]
                # no template
                elif whatsapp_message.mail_message_id.attachment_ids:
                    attachment_vals = whatsapp_message._prepare_attachment_vals(whatsapp_message.mail_message_id.attachment_ids[0], wa_account_id=whatsapp_message.wa_account_id)
                    message_type = attachment_vals.get('type')
                    send_vals = attachment_vals.get(message_type)
                    if whatsapp_message.body:
                        send_vals['caption'] = body
                else:
                    message_type = 'text'
                    send_vals = {
                        'preview_url': True,
                        'body': body,
                    }
                # Tagging parent message id if parent message is available
                if whatsapp_message.mail_message_id and whatsapp_message.mail_message_id.parent_id:
                    parent_id = whatsapp_message.mail_message_id.parent_id.wa_message_ids
                    if parent_id:
                        parent_message_id = parent_id[0].msg_uid
                msg_uid = wa_api._send_whatsapp(number=number, message_type=message_type, send_vals=send_vals, parent_message_id=parent_message_id)
            except WhatsAppError as we:
                whatsapp_message._handle_error(whatsapp_error_code=we.error_code, error_message=we.error_message,
                                               failure_type=we.failure_type)
            except (UserError, ValidationError) as e:
                whatsapp_message._handle_error(failure_type='unknown', error_message=str(e))
            else:
                if not msg_uid:
                    whatsapp_message._handle_error(failure_type='unknown')
                else:
                    if message_type == 'template':
                        whatsapp_message._post_message_in_active_channel()
                    whatsapp_message.write({
                        'state': 'sent',
                        'msg_uid': msg_uid
                    })
                if with_commit:
                    self._cr.commit()