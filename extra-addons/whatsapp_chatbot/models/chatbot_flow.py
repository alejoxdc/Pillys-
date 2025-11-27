import logging
import requests

from odoo import models, fields, SUPERUSER_ID
from odoo import api
from odoo.exceptions import UserError
from odoo.addons.base.models.res_partner import _tz_get
from datetime import datetime, timedelta
from pytz import timezone, utc
from odoo.addons.queue_job.delay import group, chain

_logger = logging.getLogger(__name__)


class ChatbotFlow(models.Model):
    _name = "whatsapp_chatbot.chatbot.flow"
    _description = "Chatbot Flow"

    name = fields.Char(string="Flow Name", required=True)
    chatbot_ids = fields.One2many(
        "whatsapp_chatbot.chatbot", "flow_id", string="Chatbots"
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("stoped", "Stoped"),
        ],
        string="State",
        default="draft",
        copy=False,
        group_expand="_group_expand_states",
    )
    wa_account_id = fields.Many2one(
        "whatsapp.account", string="WhatsApp Account", required=True
    )

    resource_calendar_id = fields.Many2one(
        "resource.calendar", string="Resource Calendar"
    )

    utm_campaign_id = fields.Many2one("utm.campaign", string="Campaign")
    utm_campaign_ids = fields.Many2many("utm.campaign", string="Campaign")

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    type = fields.Selection(
        [
            ("chatbot", "Chatbot"),
            ("agent", "AI Agent"),
        ],
        string="Type",
        default="chatbot",
    )

    webhook_url = fields.Char(
        string="Webhook URL",
        help="URL to which the webhook will send the data.",
    )

    def _group_expand_states(self, states, domain, order):
        return [key for key, val in type(self).state.selection]

    def send_webhook_request(self, message, number_or_group, name, instance, opportunity=None, partner=None):
        """
        Sends a GET request to the webhook URL with the specified query parameters.

        :param message: The message to send.
        :param number_or_group: The number or group to send the message to.
        :param name: The name associated with the request.
        :param instance: The instance identifier.
        :raises UserError: If the webhook URL is not defined or the request fails.
        """
        self.ensure_one()  # Ensure the method is called on a single record

        if not self.webhook_url:
            raise UserError("Webhook URL is not defined for this Chatbot Flow.")

        # Prepare query parameters
        params = {
            "message": message,
            "number_or_group": number_or_group,
            "name": name,
            "instance": instance,
            "opportunity": opportunity,
            "partner": partner,
        }

        try:
            # Send the GET request
            response = requests.get(self.webhook_url, params=params, timeout=180)

            # Check the response status
            if response.status_code != 200:
                raise UserError(
                    f"Failed to send request to webhook. Status code: {response.status_code}, Response: {response.text}"
                )

            return response.json()  # Return the JSON response if needed
        except requests.RequestException as e:
            raise UserError(f"An error occurred while sending the request: {str(e)}")


    def process_webhook_response(self, response):
        """
        Processes the webhook response and extracts the relevant information.

        :param response: The JSON response from the webhook.
        :return: A dictionary containing the processed response.
        :raises UserError: If the response format is invalid.
        """
        try:
            # Ensure the response is a list and contains at least one item
            if not isinstance(response, list) or not response:
                raise UserError("Invalid response format: Expected a non-empty list.")

            # Extract the first item in the response
            first_item = response[0]

            # Ensure the first item contains the expected structure
            output = first_item.get("output", {})
            response_data = output.get("response", {})

            if not isinstance(response_data, dict):
                raise UserError("Invalid response format: 'response' should be a dictionary.")

            # Extract the specific fields from the response
            first = response_data.get("first", "")
            second = response_data.get("second", "")
            third = response_data.get("third", "")

            # Log the extracted data
            _logger.info("Webhook Response Processed: First: %s, Second: %s, Third: %s", first, second, third)

            # Return the processed response as a dictionary
            return {
                "first": first,
                "second": second,
                "third": third,
            }

        except Exception as e:
            _logger.error("Error processing webhook response: %s", str(e))
            raise UserError(f"Error processing webhook response: {str(e)}")


    def handle_webhook_interaction(self, channel, message, number_or_group, name, instance):
        """
        Sends a request to the webhook, processes the response, and posts the response to the channel.

        :param channel: The channel to post the response to.
        :param message: The message to send to the webhook.
        :param number_or_group: The number or group to send the message to.
        :param name: The name associated with the request.
        :param instance: The instance identifier.
        :raises UserError: If the webhook request or response processing fails.
        """
        self.ensure_one()  # Ensure the method is called on a single record

        # Step 1: Send the webhook request
        try:
            _logger.info("Sending webhook request with message: %s", message)
            webhook_response = self.send_webhook_request(
                message=message,
                number_or_group=number_or_group,
                name=name,
                instance=instance,
                opportunity=channel.current_opportunity_id.id if channel.current_opportunity_id else None,
                partner=channel.whatsapp_partner_id.id if channel.whatsapp_partner_id else None,
            )
        except Exception as e:
            _logger.error("Failed to send webhook request: %s", str(e))
            raise UserError(f"Failed to send webhook request: {str(e)}")

        # Step 2: Process the webhook response
        try:
            _logger.info("Processing webhook response: %s", webhook_response)
            processed_response = self.process_webhook_response(webhook_response)
        except Exception as e:
            _logger.error("Failed to process webhook response: %s", str(e))
            raise UserError(f"Failed to process webhook response: {str(e)}")

        try:
            message_jobs = []
            # Iterate in the desired order (first, second, third)
            for key in ["first", "second", "third"]:
                body = processed_response.get(key)
                if body:  # Only create jobs for non-empty responses
                    kwargs = {
                        "body": body,
                        "message_type": "comment",
                        "subtype_xmlid": "mail.mt_comment",
                    }
                    # Create a delayable job for posting this specific message
                    post_job = channel.with_user(SUPERUSER_ID).delayable().whatsapp_message_post(**kwargs)
                    message_jobs.append(post_job)

            # If there are messages to send, chain them and delay the chain
            if message_jobs:
                chain(*message_jobs).delay()
                _logger.info("Enqueued chain of %d message posting jobs for channel %s.", len(message_jobs), channel.id)
            else:
                _logger.info("No non-empty messages found in processed response for channel %s.", channel.id)
        except Exception as e:
            _logger.error("Failed to create or enqueue message posting chain for channel %s: %s", channel.id, str(e))
            raise UserError(f"Failed to create or enqueue message posting chain: {str(e)}")

    @api.model
    def create(self, vals):
        record = super(ChatbotFlow, self).create(vals)
        if record.wa_account_id:
            record.wa_account_id._compute_is_bound_to_active_flow()
        return record

    @api.model
    def is_chatbot_flow_available(self):
        # Get the current date and time
        now = datetime.now()

        # Convert the current date and time to the timezone of the resource calendar
        tz = timezone(self.resource_calendar_id.tz or "UTC")
        now = now.astimezone(tz)

        # Get the day of the week (0=Monday, 6=Sunday) and the time
        day_of_week = now.weekday()
        time = now.hour + now.minute / 60.0

        # Search for an attendance record that matches the current day of the week and time
        attendance = self.env["resource.calendar.attendance"].search(
            [
                ("calendar_id", "=", self.resource_calendar_id.id),
                ("dayofweek", "=", str(day_of_week)),
                ("hour_from", "<=", time),
                ("hour_to", ">=", time),
            ],
            limit=1,
        )

        # The chatbot flow is available if an attendance record was found
        return bool(attendance)

    @api.model
    def get_chatbot_by_sequence(self, sequence):
        chatbot = self.env["whatsapp_chatbot.chatbot"].search(
            [("flow_id", "=", self.id), ("sequence", "=", sequence)], limit=1
        )
        return chatbot

    @api.model
    def get_next_chatbot(self, sequence, previous_chatbot):
        if previous_chatbot and previous_chatbot.next_chatbot_id:
            return previous_chatbot.next_chatbot_id

        final_chatbot = self.get_last_chatbot()
        if sequence == final_chatbot.sequence:
            return None

        chatbot = self.env["whatsapp_chatbot.chatbot"].search(
            [("flow_id", "=", self.id), ("sequence", ">", sequence)],
            order="sequence asc",
            limit=1,
        )

        return chatbot

    @api.model
    def get_previous_chatbot(self, channel_id):
        execution_record = self.env["chatbot.execution.record"].search(
            [("channel_id", "=", channel_id)],
            order="id desc",
            limit=1,
        )
        if execution_record:
            chatbot_id = execution_record.chatbot_id.id
            return self.env["whatsapp_chatbot.chatbot"].browse(chatbot_id)
        return None

    @api.model
    def get_first_chatbot(self):
        chatbot = self.env["whatsapp_chatbot.chatbot"].search(
            [("flow_id", "=", self.id)], order="sequence asc", limit=1
        )
        return chatbot if chatbot else None

    @api.model
    def get_last_chatbot(self):
        chatbot = self.env["whatsapp_chatbot.chatbot"].search(
            [("flow_id", "=", self.id)], order="sequence desc", limit=1
        )
        return chatbot if chatbot else None

    @api.onchange("wa_account_id")
    def _onchange_wa_account_id(self):
        for record in self:
            if record.wa_account_id:
                record.wa_account_id._compute_is_bound_to_active_flow()

    def action_start_flow(self):
        """
        check if every chatbot of template kind has a template on approved state if not raise error
        check if every chatbot of server_action kind has a server_action if not raise error
        check if every chatbot of text kind has a message_content if not raise error
        check if every chatbot has a sequence if not raise error
        """
        chatbot_errors = []
        chatbot_ids = self.chatbot_ids.sorted(key=lambda r: r.sequence)
        for chatbot in chatbot_ids:
            if chatbot.message_type == "template":
                if not chatbot.wa_template_id:
                    chatbot_errors.append(
                        "Chatbot {} of template kind has no template".format(
                            chatbot.name
                        )
                    )
                elif chatbot.wa_template_id.status != "approved":
                    chatbot_errors.append(
                        "Chatbot {} of template kind has a template on {} state".format(
                            chatbot.name, chatbot.wa_template_id.status
                        )
                    )
            elif chatbot.message_type == "server_action":
                if not chatbot.server_action_id:
                    chatbot_errors.append(
                        "Chatbot {} of server action kind has no server_action".format(
                            chatbot.name
                        )
                    )
            elif chatbot.message_type == "text":
                if not chatbot.message_content:
                    chatbot_errors.append(
                        "Chatbot {} of text kind has no message content".format(
                            chatbot.name
                        )
                    )
            else:
                chatbot_errors.append(
                    "Chatbot {} has no message type".format(chatbot.name)
                )

        if chatbot_errors:
            error_message = "\n".join(chatbot_errors)
            return {
                "type": "ir.actions.act_window",
                "name": "Error starting flow",
                "res_model": "whatsapp_chatbot.message.warning",
                "view_mode": "form",
                "target": "new",
                "context": {"default_text": error_message},
            }
        else:
            self.write({"state": "active"})

    def action_stop_flow(self):
        self.write({"state": "stoped"})

    def action_draft_flow(self):
        self.write({"state": "draft"})
