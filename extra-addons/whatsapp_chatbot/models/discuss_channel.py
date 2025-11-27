# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import re
import pytz
from datetime import datetime, timedelta
from markupsafe import Markup
from pytz import utc

from odoo import api, Command, fields, models, tools, _
from odoo.osv import expression
from odoo.addons.whatsapp.tools import phone_validation as wa_phone_validation
from odoo.addons.whatsapp_chatbot.tools.redis import RedisCache
from odoo.exceptions import ValidationError
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT


_logger = logging.getLogger(__name__)


class DiscussChannel(models.Model):
    """Support WhatsApp Channels, used for discussion with a specific
    whasapp number"""

    _inherit = "discuss.channel"

    activate_bot = fields.Boolean(string="Activate Bot", default=True)
    current_chatbot_sequence = fields.Integer(
        string="Current Chatbot Sequence", default=-1
    )
    wating_for_response = fields.Boolean(string="Waiting for response", default=False)
    final_chatbot_sequence = fields.Integer(string="Final Chatbot Sequence", default=0)
    linked_partner = fields.Boolean(string="Linked Partner", default=False)
    deactivated_on = fields.Datetime(
        string="Deactivated On",
        default=fields.Datetime.now,
        compute="_compute_deactivated_on",
        store=True,
    )
    current_opportunity_id = fields.Many2one("crm.lead", string="Current Opportunity")
    partner_category_id = fields.Many2many(
        "res.partner.category",
        string="Partner Category",
        compute="_compute_partner_category_id",
        store=True,
    )
    attention_state = fields.Boolean(string="Attention State", default=False)
    last_attention_date = fields.Datetime(string="Last Attention Date")
    last_attention_user_id = fields.Many2one("res.users", string="Last Attention User")
    recently_terminated = fields.Boolean(string="Recently Terminated", default=False, compute="_compute_recently_terminated")

    def _channel_info(self):
        channel_infos = super()._channel_info()
        channel_infos_dict = {c["id"]: c for c in channel_infos}

        for channel in self:
            channel_infos_dict[channel.id]["activate_bot"] = channel.activate_bot
            channel_infos_dict[channel.id][
                "current_chatbot_sequence"
            ] = channel.current_chatbot_sequence
            channel_infos_dict[channel.id][
                "wating_for_response"
            ] = channel.wating_for_response
            channel_infos_dict[channel.id][
                "whatsapp_partner_id"
            ] = channel.whatsapp_partner_id.id
            channel_infos_dict[channel.id]["partner_category_id"] = [
                {"id": cat.id, "name": cat.name, "color": cat.color}
                for cat in channel.partner_category_id
            ]
            channel_infos_dict[channel.id][
                "current_opportunity_id"
            ] = channel.current_opportunity_id.id
            channel_infos_dict[channel.id]["attention_state"] = channel.attention_state
            channel_infos_dict[channel.id][
                "last_message_trucated"
            ] = channel.get_last_channel_message()
            channel_infos_dict[channel.id][
                "recently_terminated"
            ] = channel.recently_terminated
        return list(channel_infos_dict.values())

    def get_last_channel_message(self):
        self.ensure_one()
        last_message = self.env["mail.message"].search(
            [("model", "=", "discuss.channel"), ("res_id", "=", self.id)],
            order="create_date desc",
            limit=1,
        )

        if not last_message:
            return None

        truncated_body = self._truncate_string(last_message.body, 15)
        if truncated_body == "":
            truncated_body = "Archivo adjunto"
        formatted_date = self._format_date_to_time_string(last_message.create_date)

        return f"{truncated_body} {formatted_date}"

    def _truncate_string(self, string, length):
        # Remove HTML tags using a regular expression
        clean_string = re.sub("<[^<]+?>", "", string)
        if len(clean_string) <= length:
            return clean_string
        return clean_string[:length] + "..."

    def _format_date_to_time_string(self, date):
        if not isinstance(date, datetime):
            raise ValueError("Invalid date object")

        # Convert the date to the America/Bogota timezone
        bogota_tz = pytz.timezone("America/Bogota")
        date_bogota = date.astimezone(bogota_tz)

        return date_bogota.strftime("%I:%M %p")

    @api.returns("self")
    def _get_whatsapp_channel(
        self,
        whatsapp_number,
        wa_account_id,
        sender_name=False,
        create_if_not_found=False,
        related_message=False,
    ):
        """Creates a whatsapp channel.

        :param str whatsapp_number: whatsapp phone number of the customer. It should
          be formatted according to whatsapp standards, aka {country_code}{national_number}.

        :returns: whatsapp discussion discuss.channel
        """
        # be somewhat defensive with number, as it is used in various flows afterwards
        # notably in 'message_post' for the number, and called by '_process_messages'
        base_number = (
            whatsapp_number
            if whatsapp_number.startswith("+")
            else f"+{whatsapp_number}"
        )
        wa_number = base_number.lstrip("+")
        wa_formatted = (
            wa_phone_validation.wa_phone_format(
                self.env.company,
                number=base_number,
                force_format="WHATSAPP",
                raise_exception=False,
            )
            or wa_number
        )

        related_record = False
        responsible_partners = self.env["res.partner"]
        channel_domain = [
            ("whatsapp_number", "=", wa_formatted),
            ("wa_account_id", "=", wa_account_id.id),
        ]
        _logger.info("Related message: %s", related_message)
        if related_message:
            related_record = self.env[related_message.model].browse(
                related_message.res_id
            )
            responsible_partners = related_record._whatsapp_get_responsible(
                related_message=related_message,
                related_record=related_record,
                whatsapp_account=wa_account_id,
            ).partner_id

            # if 'message_ids' in related_record:
            #     record_messages = related_record.message_ids
            # else:
            #     record_messages = self.env['mail.message'].search([
            #         ('model', '=', related_record._name),
            #         ('res_id', '=', related_record.id),
            #         ('message_type', '!=', 'user_notification'),
            #     ])
            # channel_domain += [
            #     ('whatsapp_mail_message_id', 'in', record_messages.ids),
            # ]
        _logger.info("Channel domain: %s", channel_domain)
        channel = self.sudo().search(channel_domain, order="create_date desc", limit=1)
        _logger.info("Channel: %s", channel)
        _logger.info("Responsible partners: %s", responsible_partners)
        _logger.info("Related record: %s", channel.channel_member_ids.partner_id)
        if responsible_partners and not channel.attention_state:
            channel = channel.filtered(
                lambda c: any(
                    r in c.channel_member_ids.partner_id for r in responsible_partners
                )
            )
        partners_to_notify = responsible_partners
        record_name = related_message.record_name
        if not record_name and related_message.res_id:
            record_name = (
                self.env[related_message.model]
                .browse(related_message.res_id)
                .display_name
            )
        _logger.info("Create if not found: %s", create_if_not_found)
        _logger.info("Channel: %s", channel)
        if not channel and create_if_not_found:
            channel = (
                self.sudo()
                .with_context(tools.clean_context(self.env.context))
                .create(
                    {
                        "name": (
                            f"{wa_formatted} ({record_name})"
                            if record_name
                            else wa_formatted
                        ),
                        "channel_type": "whatsapp",
                        "whatsapp_number": wa_formatted,
                        "whatsapp_partner_id": self.env["res.partner"]
                        ._find_or_create_from_number(wa_formatted, sender_name)
                        .id,
                        "wa_account_id": wa_account_id.id,
                        "whatsapp_mail_message_id": (
                            related_message.id if related_message else None
                        ),
                    }
                )
            )
            partners_to_notify += channel.whatsapp_partner_id
            if related_message:
                # Add message in channel about the related document
                info = _(
                    "Related %(model_name)s: ",
                    model_name=self.env["ir.model"]
                    ._get(related_message.model)
                    .display_name,
                )
                url = Markup("{base_url}/web#model={model}&id={res_id}").format(
                    base_url=self.get_base_url(),
                    model=related_message.model,
                    res_id=related_message.res_id,
                )
                related_record_name = related_message.record_name
                if not related_record_name:
                    related_record_name = (
                        self.env[related_message.model]
                        .browse(related_message.res_id)
                        .display_name
                    )
                channel.message_post(
                    body=Markup(
                        '<p>{info}<a target="_blank" href="{url}">{related_record_name}</a></p>'
                    ).format(
                        info=info, url=url, related_record_name=related_record_name
                    ),
                    message_type="comment",
                    author_id=self.env.ref("base.partner_root").id,
                    subtype_xmlid="mail.mt_note",
                )
                if hasattr(related_record, "message_post"):
                    # Add notification in document about the new message and related channel
                    info = _("A new WhatsApp channel is created for this document")
                    url = Markup(
                        "{base_url}/web#model=discuss.channel&id={channel_id}"
                    ).format(base_url=self.get_base_url(), channel_id=channel.id)
                    related_record.message_post(
                        author_id=self.env.ref("base.partner_root").id,
                        body=Markup(
                            '<p>{info}<a target="_blank" class="o_whatsapp_channel_redirect"'
                            'data-oe-id="{channel_id}" href="{url}">{channel_name}</a></p>'
                        ).format(
                            info=info,
                            url=url,
                            channel_id=channel.id,
                            channel_name=channel.display_name,
                        ),
                        message_type="comment",
                        subtype_xmlid="mail.mt_note",
                    )
            if (
                partners_to_notify == channel.whatsapp_partner_id
                and wa_account_id.notify_user_ids.partner_id
            ):
                partners_to_notify += wa_account_id.notify_user_ids.partner_id
            channel.channel_member_ids = [Command.clear()] + [
                Command.create({"partner_id": partner.id})
                for partner in partners_to_notify
            ]
            channel._broadcast(partners_to_notify.ids)

            if not channel.linked_partner:
                contact = channel.whatsapp_partner_id

                info = _("Related %(model_name)s: ", model_name="Contact")

                url = Markup("{base_url}/web#model={model}&id={res_id}").format(
                    base_url=channel.get_base_url(),
                    model="res.partner",
                    res_id=contact.id,
                )
                channel.message_post(
                    body=Markup(
                        '<p>{info}<a target="_blank" href="{url}">{related_record_name}</a></p>'
                    ).format(info=info, url=url, related_record_name=contact.name),
                    message_type="comment",
                    author_id=self.env.ref("base.partner_root").id,
                    subtype_xmlid="mail.mt_note",
                )
                channel.linked_partner = True
        else:
            contact = channel.whatsapp_partner_id
            channel.sudo().with_context(tools.clean_context(self.env.context)).write(
                {
                    "name": (
                        f"{wa_formatted} ({contact.name})" if contact else wa_formatted
                    )
                }
            )

        crm_lead = self.env["crm.lead"].search(
            [
                ("partner_id", "=", channel.whatsapp_partner_id.id),
                "|",
                ("active", "=", False),
                ("stage_id.is_won", "=", False),
            ],
            limit=1,
        )
        channel.current_opportunity_id = crm_lead.id if crm_lead else False

        return channel

    @api.depends("activate_bot")
    def _compute_deactivated_on(self):
        for record in self:
            if record.activate_bot == False:
                record.deactivated_on = fields.Datetime.now()
            else:
                record.deactivated_on = False

    @api.model
    def reactivate_bots(self):
        # Get the current date and time in UTC
        now = datetime.now(utc)
        # Calculate the datetime 24 hours ago
        three_hours_ago = now - timedelta(hours=3)
        # Search for channels where activate_bot is False and deactivated_on is more than 24 hours ago
        channels = self.env["discuss.channel"].search(
            [
                ("activate_bot", "=", False),
                ("deactivated_on", "<=", three_hours_ago),
            ]
        )

        # Reactivate the bots for these channels
        channels.write({"activate_bot": True, "current_chatbot_sequence": -1})

    @api.depends("whatsapp_partner_id.category_id")
    @api.onchange("whatsapp_partner_id.category_id")
    def _compute_partner_category_id(self):
        for record in self:
            # Remove all categories from the channel
            record.write({"partner_category_id": [(5, 0, 0)]})
            for cat in record.whatsapp_partner_id.category_id:
                record.write({"partner_category_id": [(4, cat.id)]})

    @api.model
    def reactivate_bots_at_close(self):
        # Get the current date and time in UTC
        now = datetime.now(utc)

        # Calculate the datetime 24 hours ago
        twenty_four_hours_ago = now - timedelta(hours=24)
        # Search for channels where activate_bot is False and create_date is between 24 hours ago and now
        channels = self.env["discuss.channel"].search(
            [
                ("activate_bot", "=", False),
                ("deactivated_on", ">=", twenty_four_hours_ago),
                ("deactivated_on", "<=", now),
            ]
        )
        # Reactivate the bots for these channels
        channels.write({"activate_bot": True, "current_chatbot_sequence": -1})

    def set_conversation_free(self):
        for channel in self:
            members = channel.wa_account_id.notify_user_ids.mapped("partner_id").ids
            channel.add_members(members,post_joined_message=False)
            channel_name = "attention_state_fetched"
            message = {
                "channel_id": channel.id,
                "attention_state": False,
                "partner_id": self.env.user.partner_id.id,
                "last_attention_date": channel.last_attention_date,
                "recently_terminated": channel.recently_terminated
            }
            self.env["bus.bus"]._sendone(channel_name, "notification", message)
        

    def attention_state_fetched(self, new_state):
        """Update the attention_state for every member of the channel"""

        for channel in self:
            if channel.channel_type not in {"whatsapp"}:
                return
            if new_state:
                # If the new state is True (attention required), unpin the channel for all members except the current user
                cat = self.env["crm.tag"].search([("name", "=", "En atención")], limit=1)
                if not cat:
                    cat = self.env["crm.tag"].create({"name": "En atención"})
                if channel.current_opportunity_id:
                    for tag in channel.current_opportunity_id.tag_ids:
                        if tag.name == "Finalizado":
                            channel.current_opportunity_id.write({"tag_ids": [(3, tag.id)]})
                        if tag.name == "Por atender":
                            channel.current_opportunity_id.write({"tag_ids": [(3, tag.id)]})
                self.unpin_channel_for_others()
                channel.write(
                    {
                        "last_attention_date": False,
                        "last_attention_user_id": False,
                        "activate_bot": False,
                    }
                )
            else:
                cat = self.env["crm.tag"].search([("name", "=", "Finalizado")], limit=1)
                if not cat:
                    cat = self.env["crm.tag"].create({"name": "Finalizado"})
                # check if the current opportunity has a tag named "Atendiendo"
                # if it does, remove it
                if channel.current_opportunity_id:
                    for tag in channel.current_opportunity_id.tag_ids:
                        if tag.name == "En atención":
                            channel.current_opportunity_id.write({"tag_ids": [(3, tag.id)]})
                        if tag.name == "Por atender":
                            channel.current_opportunity_id.write({"tag_ids": [(3, tag.id)]})

                members = channel.wa_account_id.notify_user_ids.mapped("partner_id").ids
                channel.add_members_silently(members)
                channel.channel_pin()
                channel.write(
                    {
                        "last_attention_date": fields.Datetime.now(),
                        "last_attention_user_id": self.env.user.id
                    }
                )
            channel.current_opportunity_id.write({"tag_ids": [(4, cat.id)]})
            channel_name = "attention_state_fetched"
            message = {
                "channel_id": channel.id,
                "attention_state": new_state,
                "partner_id": self.env.user.partner_id.id,
                "last_attention_date": channel.last_attention_date,
                "recently_terminated": channel.recently_terminated,
                "activate_bot": channel.activate_bot,
            }

            self.env["bus.bus"]._sendone(channel_name, "notification", message)
    
    @api.depends("last_attention_date")
    def _compute_recently_terminated(self):
        for record in self:
            now = datetime.now(pytz.UTC)
            twenty_four_hours_ago = now - timedelta(hours=24)
            
            # Check if last_attention_date is naive or aware
            if record.last_attention_date:
                if record.last_attention_date.tzinfo is None:
                    # last_attention_date is naive
                    last_attention_date = record.last_attention_date.replace(tzinfo=None)
                    twenty_four_hours_ago = twenty_four_hours_ago.replace(tzinfo=None)
                    now = now.replace(tzinfo=None)
                else:
                    # last_attention_date is aware
                    last_attention_date = record.last_attention_date

                if twenty_four_hours_ago <= last_attention_date <= now:
                    record.recently_terminated = True
                else:
                    record.recently_terminated = False
            else:
                record.recently_terminated = False

    def unpin_channel_for_others(self):
        self.ensure_one()
        current_partner_id = self.env.user.partner_id.id

        # Find all members of the channel except the current user and who are internal users
        internal_user_group = self.env.ref(
            "base.group_user"
        )  # Reference to the internal user group
        members = self.env["discuss.channel.member"].search(
            [
                ("channel_id", "=", self.id),
                ("partner_id", "!=", current_partner_id),
                ("partner_id.user_ids.groups_id", "in", [internal_user_group.id]),
            ]
        )
        if not members:
            return True
        partners = members.mapped("partner_id")

        channel_info = self._channel_info()[
            0
        ]  # must be computed before leaving the channel (access rights)
        members.unlink()
        channel_info["is_pinned"] = False
        # Notify each member about the unpin action
        self.env["bus.bus"]._sendmany(
            [(partner, "discuss.channel/leave", channel_info) for partner in partners]
        )

    def current_opportunity_stage(self):
        self.ensure_one()
        if self.current_opportunity_id:
            _logger.info(
                "Current opportunity stage: %s",
                self.current_opportunity_id.stage_id.name,
            )
            _logger.info(
                "Current opportunity stage id: %s",
                self.current_opportunity_id.stage_id.id,
            )
            return self.current_opportunity_id.stage_id.id
        return False

    def update_opportunity_stage(self, stage_id):
        opportunity = self.current_opportunity_id

        stage = self.env["crm.stage"].browse(int(stage_id))

        if opportunity:
            opportunity.write({"stage_id": stage.id})
    
    def add_members_silently(self, partner_ids=None, guest_ids=None, open_chat_window=False):
        """ Adds the given partner_ids and guest_ids as member of self channels. """
        current_partner, current_guest = self.env["res.partner"]._get_current_persona()
        partners = self.env['res.partner'].browse(partner_ids or []).exists()
        guests = self.env['mail.guest'].browse(guest_ids or []).exists()
        all_new_members = self.env["discuss.channel.member"]
        notifications = []
        for channel in self:
            members_to_create = []
            existing_members = self.env['discuss.channel.member'].search(expression.AND([
                [('channel_id', '=', channel.id)],
                expression.OR([
                    [('partner_id', 'in', partners.ids)],
                    [('guest_id', 'in', guests.ids)]
                ])
            ]))
            members_to_create += [{
                'partner_id': partner.id,
                'channel_id': channel.id,
            } for partner in partners - existing_members.partner_id]
            members_to_create += [{
                'guest_id': guest.id,
                'channel_id': channel.id,
            } for guest in guests - existing_members.guest_id]
            new_members = self.env['discuss.channel.member'].create(members_to_create)
            all_new_members += new_members
            all_new_members.write({'is_pinned': False})
            for member in new_members.filtered(lambda member: member.partner_id):
                # notify invited members through the bus
                user = member.partner_id.user_ids[0] if member.partner_id.user_ids else self.env['res.users']
                if user:
                    channel_info = member.channel_id.with_user(user).with_context(allowed_company_ids=user.company_ids.ids)._channel_info()[0]
                    channel_info['state'] = 'closed'
                    channel_info['message_unread_counter'] = 0
                    channel_info['is_pinned'] = False
                    
                    notifications.append((member.partner_id, 'discuss.channel/joined', {
                        'channel': channel_info,
                        'invited_by_user_id': self.env.user.id,
                        'open_chat_window': open_chat_window,
                    }))

            notifications.append((channel, 'mail.record/insert', {
                'Thread': {
                    'channelMembers': [('ADD', list(new_members._discuss_channel_member_format().values()))],
                    'id': channel.id,
                    'memberCount': channel.member_count,
                    'model': "discuss.channel",
                }
            }))

            if existing_members and (current_partner or current_guest):
                # If the current user invited these members but they are already present, notify the current user about their existence as well.
                # In particular this fixes issues where the current user is not aware of its own member in the following case:
                # create channel from form view, and then join from discuss without refreshing the page.
                notifications.append((current_partner or current_guest, 'mail.record/insert', {
                    'Thread': {
                        'channelMembers': [('ADD', list(existing_members._discuss_channel_member_format().values()))],
                        'id': channel.id,
                        'memberCount': channel.member_count,
                        'model': "discuss.channel",
                    }
                }))

            self.env['bus.bus']._sendmany(notifications)
            
        return all_new_members

    def get_channel_members_but_current(self):
        self.ensure_one()
        current_user_id = self.env.user.partner_id.id
        members = self.wa_account_id.notify_user_ids
        if not members:
            return True
        members_list = []
        for member in members:
            if member.partner_id.id != current_user_id:
                members_list.append({
                    "id": member.partner_id.id,
                    "name": member.partner_id.name,
                })
        return members_list

    def delegate_channel(self, partner_id):
        self.ensure_one()
        partner = self.env["res.partner"].browse(int(partner_id))
        self.add_members([partner.id], post_joined_message=True)

        current_partner_id = self.env.user.partner_id.id
        members = self.env["discuss.channel.member"].search(
            [
                ("channel_id", "=", self.id),
                ("partner_id", "=", current_partner_id)
            ]
        )
        partners = members.mapped("partner_id")
        channel_info = self._channel_info()[
            0
        ]  # must be computed before leaving the channel (access rights)
        members.unlink()
        channel_info["is_pinned"] = False
        # Notify each member about the unpin action
        self.env["bus.bus"]._sendmany(
            [(partner, "discuss.channel/leave", channel_info) for partner in partners]
        )
        return True
    
    def whatsapp_message_post(self, **kwargs):
        new_msg = self.message_post(**kwargs)
        cache = RedisCache()
        db_name = self._cr.dbname
        if not new_msg.wa_message_ids:
            whatsapp_message = self.env['whatsapp.message'].create({
                'body': new_msg.body,
                'mail_message_id': new_msg.id,
                'message_type': 'outbound',
                'mobile_number': f'+{self.whatsapp_number}',
                'wa_account_id': self.wa_account_id.id,
            })
            # Generar una clave única para el mensaje
            message_key = f"message_sent_{db_name}_discuss_channel_{self.id}_{hash(new_msg.body)}"
            # Verificar si el mensaje ya ha sido enviado
            cached_value = cache.get_value(message_key)
            if not cached_value:
                whatsapp_message._send()
                cache.set_value(message_key, new_msg.body, ex=300)  # Expira en 5 minutos
            else:
                _logger.info("Message already sent, skipping sending.")
            new_msg.write({
                'wa_message_ids': [(4, whatsapp_message.id)],
                'message_type': 'whatsapp_message',
            })
        return new_msg
