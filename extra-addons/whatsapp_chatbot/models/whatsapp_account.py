import logging
import mimetypes

from odoo import fields, models, SUPERUSER_ID
from odoo import api
from odoo.addons.whatsapp.tools.whatsapp_api import WhatsAppApi
from markupsafe import Markup
from odoo.tools.translate import _
from odoo.addons.whatsapp.tools import phone_validation as wa_phone_validation
from odoo.tools import plaintext2html
from odoo.addons.whatsapp_chatbot.models.whatsapp_account_inherited import (
    WhatsappAccountInherited,
)
from datetime import datetime, timedelta
from pytz import utc

_logger = logging.getLogger(__name__)


class WhatsappAccount(WhatsappAccountInherited):
    _inherit = "whatsapp.account"

    is_bound_to_active_flow = fields.Boolean(
        compute="_compute_is_bound_to_active_flow", store=True
    )

    def _get_active_chatbot_flows(self, campaign_id):
        for rec in self:
            search_conditions = [
                ("state", "=", "active"),
                ("wa_account_id", "=", rec.id),
            ]
            if campaign_id:
                search_conditions.append(("utm_campaign_ids", "in", [campaign_id.id]))
                active_flows = self.env["whatsapp_chatbot.chatbot.flow"].search(
                    search_conditions
                )
                if active_flows:
                    return active_flows
                else:
                    search_conditions = [
                        ("state", "=", "active"),
                        ("wa_account_id", "=", rec.id),
                        ("utm_campaign_ids", "=", False)
                    ]
                    active_flows = self.env["whatsapp_chatbot.chatbot.flow"].search(
                        search_conditions
                    )
                    return active_flows
            else:
                search_conditions.append(("utm_campaign_ids", "=", False))

            active_flows = self.env["whatsapp_chatbot.chatbot.flow"].search(
                search_conditions
            )
            return active_flows

    def _compute_is_bound_to_active_flow(self):
        ChatbotFlow = self.env["whatsapp_chatbot.chatbot.flow"]
        for record in self:
            active_flow = ChatbotFlow.search(
                [("wa_account_id", "=", record.id)], limit=1
            )
            record.is_bound_to_active_flow = bool(active_flow)

    def _process_messages(self, value):
        super()._process_messages(value)

        for messages in value.get("messages", []):
            sender_name = value.get("contacts", [{}])[0].get("profile", {}).get("name")
            sender_mobile = messages["from"]
            channel = self._find_active_channel(
                sender_mobile, sender_name=sender_name, create_if_not_found=False
            )
            if not channel:
                return
            contact = channel.whatsapp_partner_id
            message_type = messages["type"]
            if channel:
                source_id, campaign_origin = self.identify_campaign(messages)
                if source_id and campaign_origin:
                    channel.current_opportunity_id.assign_campaign(
                        source_id, campaign_origin
                    )
                campaign_id = None
                if source_id:
                    ad = self.env['utm.campaign.ad'].search([('name', '=', source_id)])
                    if ad:
                        campaign_id = ad.utm_campaign_id
                chatbot_flows = self._get_active_chatbot_flows(
                    campaign_id
                )
                _logger.info("Chatbot flows: %s", chatbot_flows)
                for chatbot_flow in chatbot_flows:
                    if chatbot_flow.is_chatbot_flow_available():
                        if channel.activate_bot:
                            _logger.info(
                                "Processing message for channel %s", channel.id
                            )
                            _logger.info("Chatbot flow: %s", chatbot_flow.name)
                            _logger.info(
                                "Chatbot sequence: %s", channel.current_chatbot_sequence
                            )
                            _logger.info(
                                "Chatbot activate bot: %s", channel.activate_bot
                            )
                            _logger.info(
                                "Chatbot waiting for response: %s",
                                channel.wating_for_response,
                            )
                            _logger.info(
                                "Chatbot deactivated on: %s", channel.deactivated_on
                            )
                            _logger.info("Chatbot partner: %s", channel.name)
                            _logger.info("Message type: %s", message_type)
                            if message_type in ["text", "button"]:
                                message_content = (
                                    messages["text"]["body"]
                                    if message_type == "text"
                                    else messages["button"]["text"]
                                )
                                kwargs = {
                                    "body": message_content,
                                    "subtype_xmlid": "mail.mt_comment",
                                }
                                contact.message_post(**kwargs)
                                if chatbot_flow.type == "chatbot":
                                    self._eval_next_step(chatbot_flow, channel, messages)
                                else:
                                    message_content = (
                                        messages["text"]["body"]
                                        if message_type == "text"
                                        else messages["button"]["text"]
                                    )
                                    _logger.info(
                                        "Message content: %s", message_content
                                    )
                                    chatbot_flow.with_delay().handle_webhook_interaction(
                                        channel, message_content, sender_mobile, sender_name, instance="trials")


    # create a recursive function to get the next step in the flow and send the message to the user the stop condition is when the variable channel.wating_for_response is False
    def _eval_next_step(self, chatbot_flow, channel, messages=None):
        chatbot = None
        previous_chatbot = None
        send_previous_chatbot = False
        message_type = messages["type"]
        execution_state = "completed"
        message_content = (
            messages["text"]["body"]
            if message_type == "text"
            else messages["button"]["text"]
        )
        if channel.current_chatbot_sequence == -1:
            chatbot = chatbot_flow.get_first_chatbot()
        else:
            previous_chatbot = chatbot_flow.get_previous_chatbot(channel.id)
            chatbot = chatbot_flow.get_next_chatbot(
                channel.current_chatbot_sequence, previous_chatbot
            )
             
        if previous_chatbot:
            execute_bot_run_once = not previous_chatbot.run_once or (
                previous_chatbot.run_once
                and previous_chatbot.chatbot_executed_by_partner(
                    channel.whatsapp_partner_id.id
                )
                and not previous_chatbot.check_for_ignored
            )

            if execute_bot_run_once:
                if previous_chatbot.message_intention == "open_question":
                    if previous_chatbot.message_action == "update_name":
                        channel.whatsapp_partner_id.write({"name": message_content})
                
                elif previous_chatbot.message_intention == "mult_choice_question":
                    _logger.info("Mult choice question")
                    _logger.info("Message content: %s", message_content)
                    _logger.info("Previous chatbot: %s", previous_chatbot.name)
                    if not previous_chatbot.check_for_completed(
                        channel.whatsapp_partner_id.id
                    ):
                        send_previous_chatbot = True
                        for child in previous_chatbot.child_ids:
                            if child.button_id:
                                _logger.info(
                                    "Child button id: %s", child.button_id.name
                                )
                                _logger.info("Message content: %s", message_content)
                                if child.button_id.name == message_content:
                                    chatbot = child
                                    send_previous_chatbot = False
                                    break
                        if send_previous_chatbot:
                            counter = (
                                previous_chatbot.count_incomplete_chatbot_executions(
                                    channel.whatsapp_partner_id.id, previous_chatbot
                                )
                            )
                            if counter < 3:
                                kwargs = {
                                    "body": "Por favor selecciona una de las opciones disponibles",
                                    "message_type": "whatsapp_message",
                                    "subtype_xmlid": "mail.mt_comment",
                                }
                                channel.with_user(SUPERUSER_ID).message_post(**kwargs)
                                chatbot = previous_chatbot
                            else:
                                kwargs = {
                                    "body": "No pudimos entender tu respuesta, en un momento un asesor se comunicará contigo",
                                    "message_type": "whatsapp_message",
                                    "subtype_xmlid": "mail.mt_comment",
                                }
                                channel.with_user(SUPERUSER_ID).message_post(**kwargs)
                                chatbot = None

        if chatbot:
            current_sequence = (
                chatbot.sequence
                if not chatbot.parent_id
                else chatbot.get_root_chatbot().sequence
            )
            _logger.info("Current sequence: %s", current_sequence)
            if not chatbot.is_active:
                channel.current_chatbot_sequence = current_sequence
                execution_state = "ignored"
                self._eval_next_step(chatbot_flow, channel, messages)
                return

            if chatbot.run_once:
                if chatbot.chatbot_executed_by_partner(channel.whatsapp_partner_id.id):
                    channel.current_chatbot_sequence = current_sequence
                    execution_state = "ignored"
                    self._eval_next_step(chatbot_flow, channel, messages)
                    return

            channel.current_chatbot_sequence = current_sequence
            if chatbot.bot_action == "go_to":
                chatbot.create_execution_record(
                    channel, channel.whatsapp_partner_id.id, execution_state
                )
                chatbot.next_chatbot_id.set_last_execution_record_as_uncompelted(
                    channel.whatsapp_partner_id.id
                )
                if previous_chatbot:
                    if not send_previous_chatbot:
                        previous_chatbot.set_last_execution_record_as_compelted(
                            channel.whatsapp_partner_id.id
                        )
                self._eval_next_step(chatbot_flow, channel, messages)
                return

            if chatbot.message_intention != "info":
                channel.wating_for_response = True
                execution_state = "uncompleted"
            else:
                channel.wating_for_response = False

            if chatbot.message_type == "text":
                body = chatbot.message_content
                kwargs = {
                    "body": body,
                    "message_type": "whatsapp_message",
                    "subtype_xmlid": "mail.mt_comment",
                }
                channel.with_user(SUPERUSER_ID).message_post(**kwargs)
            # TODO: add tz to chatbot flow
            elif chatbot.message_type == "template":
                _logger.info("Sending template")
                _logger.info("Channel: %s", channel)
                whatsapp_composer = (
                    self.env["whatsapp.composer"]
                    .with_context(
                        {
                            "active_model": chatbot.wa_template_id.model,
                            "active_id": channel.whatsapp_partner_id.id,
                            "lang": channel.whatsapp_partner_id.lang,
                            "tz": "America/Bogota",
                            "uid": SUPERUSER_ID,
                        }
                    )
                    .with_user(SUPERUSER_ID)
                    .create(
                        {
                            "phone": channel.whatsapp_number,
                            "wa_template_id": chatbot.wa_template_id.id,
                            "res_model": chatbot.wa_template_id.model,
                        }
                    )
                )
                whatsapp_composer.with_user(SUPERUSER_ID)._send_whatsapp_template(
                    force_send_by_cron=False
                )
            _logger.info("Create Chatbot ER: %s", chatbot.name)
            chatbot.create_execution_record(
                channel, channel.whatsapp_partner_id.id, execution_state
            )
            if previous_chatbot:
                if not send_previous_chatbot:
                    previous_chatbot.set_last_execution_record_as_compelted(
                        channel.whatsapp_partner_id.id
                    )

            if not channel.wating_for_response:
                self._eval_next_step(chatbot_flow, channel, messages)

        else:
            channel.current_chatbot_sequence = -1
            channel.wating_for_response = False
            channel.activate_bot = False
            channel.deactivated_on = fields.Datetime.now()
