import logging
from odoo import api, Command, fields, models, tools, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class Chatbot(models.Model):
    _name = "whatsapp_chatbot.chatbot"
    _description = "Chatbot"

    name = fields.Char(string="Name", required=True)
    message_type = fields.Selection(
        [
            ("text", "Text"),
            ("template", "Template"),
            ("server_action", "Server Action"),
        ],
        string="Message Type",
        required=True,
    )
    message_intention = fields.Selection(
        [
            ("info", "Send info"),
            ("open_question", "Open question"),
            ("mult_choice_question", "Multiple choice question"),
        ],
        string="Message Intention",
        required=True,
    )
    message_action = fields.Selection(
        [
            ("create", "Create"),
            ("update", "Update"),
        ],
        string="Message Action",
    )
    action_model_create = fields.Selection(
        [
            ("res.partner", "Partner"),
            ("crm.lead", "Lead"),
            ("sale.order", "Sale Order"),
            ("helpdesk.ticket", "Ticket"),
        ],
        string="Action Model",
    )

    action_model_update = fields.Selection(
        [
            ("res.partner", "Partner"),
        ],
        string="Action Model",
    )

    # partner fields

    partner_type = fields.Selection(
        [
            ("contact", "Contact"),
            ("invoice", "Invoice"),
            ("delivery", "Delivery"),
            ("other", "Other"),
        ],
        string="Partner Type",
    )

    def _get_partner_fields(self):
        partner_fields = self.env['res.partner'].fields_get()
        field_list = []
        for field_name, field_info in partner_fields.items():
            if field_info['type'] in ['char', 'selection']:
                # Include the technical name in the label
                label = f"{field_info['string']} ({field_name})"
                field_list.append((field_name, label))
        # Sort the field list alphabetically by field name
        field_list.sort(key=lambda x: x[1])
        return field_list

    partner_field = fields.Selection(
        selection=_get_partner_fields,
        string="Partner Field",
    )

    res_partner_l10n_latam_identification_type_id = fields.Many2one(
        "l10n_latam.identification.type",
        string="Identification Type",
        index="btree_not_null",
        auto_join=True,
        default=lambda self: self.env.ref(
            "l10n_latam_base.it_vat", raise_if_not_found=False
        ),
        help="The type of identification",
    )

    res_partner_category_id = fields.Many2many("res.partner.category", string="Tags")
    # end partner fields
    
    # CRM LEAD FIELDS
    crm_lead_field = fields.Selection(
        [
            ("name", "Name"),
            ("tag_ids", "Tags"),
            ("priority", "Priority"),
        ],
        string="Lead Field",
    )
    crm_lead_tag_ids = fields.Many2many(
        'crm.lead.tag', 
        'crm_lead_tag_rel',  # Another unique relation table
        'chatbot_id', 
        'tag_id', 
        string='CRM Lead Tags'
    )
    crm_lead_priority = fields.Selection(
        [
            ("0", "Low"),
            ("1", "Normal"),
            ("2", "High"),
            ("3", "Very High"),
        ],
        string="Priority",
    )
    # END CRM LEAD FIELDS
    # SALE ORDER FIELDS
    sale_order_product_id = fields.Many2one("product.product", string="Product")
    # END SALE ORDER FIELDS
    # HELPDESK TICKET FIELDS
    helpdesk_ticket_field = fields.Selection(
        [
            ("name", "Name"),
            ("tag_ids", "Tags"),
            ("priority", "Priority"),
            ("ticket_type_id", "Type"),
        ],
        string="Ticket Field",
    )
    helpdesk_ticket_tag_ids = fields.Many2many(
        'helpdesk.tag', 
        'helpdesk_tag_rel',  # Unique relation table
        'chatbot_id', 
        'tag_id', 
        string='Helpdesk Ticket Tags'
    )
    helpdesk_ticket_priority = fields.Selection(
        [
            ("0", "Low"),
            ("1", "Normal"),
            ("2", "High"),
            ("3", "Very High"),
        ],
        string="Priority",
    )
    helpdesk_ticket_type_id = fields.Many2one("helpdesk.ticket.type", string="Type")

    message_content = fields.Text(string="Message Content")
    server_action_id = fields.Many2one(
        comodel_name="ir.actions.server", string="Server Action"
    )
    wa_template_id = fields.Many2one(
        comodel_name="whatsapp.template", string="Template"
    )
    flow_id = fields.Many2one(
        comodel_name="whatsapp_chatbot.chatbot.flow", string="Chatbot Flow"
    )
    sequence = fields.Integer(string="Sequence")

    parent_id = fields.Many2one(
        comodel_name="whatsapp_chatbot.chatbot", string="Parent Chatbot"
    )

    child_ids = fields.One2many(
        comodel_name="whatsapp_chatbot.chatbot",
        inverse_name="parent_id",
        string="Child Chatbots",
    )
    # Agregando el campo is_active como un interruptor
    is_active = fields.Boolean(default=True)
    run_once = fields.Boolean(string="Run Once")
    chatbot_execution_ids = fields.One2many(
        comodel_name="chatbot.execution.record",
        inverse_name="chatbot_id",
        string="Chatbot Executions",
    )
    button_id = fields.Many2one(
        comodel_name="whatsapp.template.button", string="Button"
    )
    next_chatbot_id = fields.Many2one(
        comodel_name="whatsapp_chatbot.chatbot", string="Next Chatbot"
    )
    bot_action = fields.Selection(
        [
            ("send_message", "Send Message"),
            ("go_to", "Go to another chatbot"),
        ],
        default="send_message",
        string="Bot Action",
    )

    # order this class by sequence
    _order = "sequence asc, id"

    @api.model
    def create(self, vals):
        record = super(Chatbot, self).create(vals)
        # froce sequence to be the last one
        if not vals.get("sequence"):
            last_sequence = (
                self.env["whatsapp_chatbot.chatbot"]
                .search(
                    [("flow_id", "=", record.flow_id.id)],
                    order="sequence desc",
                    limit=1,
                )
                .read(["sequence"])
            )
            record.sequence = last_sequence[0]["sequence"] + 1 if last_sequence else 0

        # parent_id = vals.get("parent_id")
        # if parent_id:
        #     chatbot = self.browse(parent_id)
        #     if chatbot and (chatbot.id == self.id or self.id in chatbot.child_ids.ids):
        #         raise ValidationError(
        #             "Invalid parent_id value. Cannot set parent as self or child."
        #         )

        if vals.get("message_type") == "template":
            template = self.env["whatsapp.template"].browse(vals.get("wa_template_id"))
            if template and template.button_ids:
                for button in template.button_ids:
                    if button.button_type == "quick_reply":
                        chatbot_vals = {
                            "name": button.name,
                            "message_type": "text",
                            "message_intention": "info",
                            "message_content": button.name,
                            "button_id": button.id,
                            "parent_id": record.id,
                        }
                        self.create(chatbot_vals)
        return record

    @api.model
    def write(self, vals):
        record = super(Chatbot, self).write(vals)
        parent_id = vals.get("parent_id")

        if parent_id:
            _logger.info(f"parent_id: {parent_id}")
            chatbot = self.browse(parent_id)
            if chatbot and (chatbot.id == self.id or self.id in chatbot.child_ids.ids):
                raise ValidationError(
                    "Invalid parent_id value. Cannot set parent as self or child."
                )

        if vals.get("message_type") == "template":
            template = self.env["whatsapp.template"].browse(vals.get("wa_template_id"))
            if template and template.button_ids:
                for button in template.button_ids:
                    if button.button_type == "quick_reply":
                        chatbot_vals = {
                            "name": button.name,
                            "message_type": "text",
                            "message_intention": "info",
                            "message_content": button.name,
                            "button_id": button.id,
                            "parent_id": self.id,
                        }
                        self.create(chatbot_vals)

        return record

    def chatbot_executed_by_partner(self, partner_id):
        self.ensure_one()
        return self.chatbot_execution_ids.filtered(
            lambda r: r.partner_id.id == partner_id
        )

    def create_execution_record(self, channel, partner_id, state="completed"):
        self.ensure_one()
        return self.env["chatbot.execution.record"].create(
            {
                "chatbot_id": self.id,
                "channel_id": channel.id,
                "partner_id": partner_id,
                "state": state,
            }
        )

    def check_for_ignored(self, partner_id):
        self.ensure_one()
        ignored_record = self.env["chatbot.execution.record"].search(
            [
                ("chatbot_id", "=", self.id),
                ("partner_id", "=", partner_id),
                ("state", "=", "ignored"),
            ],
            limit=1,
        )
        return bool(ignored_record)

    def check_for_completed(self, partner_id):
        self.ensure_one()
        time_limit = datetime.now() - timedelta(days=1)
        
        # Get the last record for the partner within the time limit
        last_record = self.env["chatbot.execution.record"].search(
            [
                ("partner_id", "=", partner_id),
                ("execution_time", ">=", time_limit),
            ],
            order="id desc",
            limit=1,
        )

        # Get the completed record for the chatbot and partner within the time limit
        completed_record = self.env["chatbot.execution.record"].search(
            [
                ("chatbot_id", "=", self.id),
                ("partner_id", "=", partner_id),
                ("state", "=", "completed"),
                ("execution_time", ">=", time_limit),
            ],
            limit=1,
        )

        # Check if last record and completed record match
        if last_record and completed_record and last_record.id == completed_record.id:
            return True

        # Check if the last record state is completed
        if last_record and last_record.state == "completed":
            return True

        return False

    def set_last_execution_record_as_compelted(self, partner_id):
        self.ensure_one()
        last_record = self.env["chatbot.execution.record"].search(
            [
                ("chatbot_id", "=", self.id),
                ("partner_id", "=", partner_id),
            ],
            order="id desc",
            limit=1,
        )
        if last_record and last_record.state == "uncompleted":
            last_record.write({"state": "completed"})
        return last_record
    
    def set_last_execution_record_as_uncompelted(self, partner_id):
        self.ensure_one()
        last_record = self.env["chatbot.execution.record"].search(
            [
                ("chatbot_id", "=", self.id),
                ("partner_id", "=", partner_id),
            ],
            order="id desc",
            limit=1,
        )
        if last_record and last_record.state == "completed":
            last_record.write({"state": "uncompleted"})
        return last_record

    def get_root_chatbot(self):
        self.ensure_one()
        root_chatbot = self
        while root_chatbot.parent_id:
            root_chatbot = root_chatbot.parent_id
        return root_chatbot

    def count_incomplete_chatbot_executions(self, partner_id, chatbot):
        self.ensure_one()
        incomplete_executions = chatbot.chatbot_execution_ids.filtered(
            lambda r: r.partner_id.id == partner_id and r.state == "uncompleted"
        )
        return len(incomplete_executions)