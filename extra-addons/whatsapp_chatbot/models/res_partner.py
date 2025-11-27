import logging
from odoo import api, fields, models, _, SUPERUSER_ID

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _find_or_create_from_number(self, number, name=False):
        partner = super()._find_or_create_from_number(number, name)

        # Check if the partner has any opportunities in a state below 'is_won'
        opportunitie = self.env["crm.lead"].search(
            [
                ("partner_id", "=", partner.id),
                ("won_status", "=", "pending"),
                ("active", "=", True),
            ],
            limit=1,
        )

        # If not, create a new opportunity
        if not opportunitie:
            opportunitie = self.env["crm.lead"].create(
                {
                    "name": _("Oportunidad creada desde WhatsApp"),
                    "partner_id": partner.id,
                    "date_deadline": fields.Date.today(),
                    # Add any other necessary fields here
                }
            )

        cat = self.env["crm.tag"].search([("name", "=", "Por atender")], limit=1)
        if not cat:
            cat = self.env["crm.tag"].create({"name": "Por atender"})

        opportunitie.write({"tag_ids": [(4, cat.id)]})

        return partner

    def _send_template(
        self, wa_template, user_id=SUPERUSER_ID, force_send_by_cron=False
    ):
        for rec in self:
            _logger.info(
                "Sending WhatsApp template %s to %s", wa_template.name, rec.name
            )
            model = self.env[wa_template.model_id.model]
            record_obj = model.browse(rec.id)
            phone_number = getattr(record_obj, wa_template.phone_field, None)

            if phone_number:
                whatsapp_composer = (
                    self.env["whatsapp.composer"]
                    .with_context(
                        {
                            "active_model": wa_template.model_id.model,
                            "active_id": rec.id,
                        }
                    )
                    .with_user(user_id)
                    .create(
                        {
                            "phone": phone_number,
                            "wa_template_id": wa_template.id,
                            "res_model": wa_template.model_id.model,
                        }
                    )
                )
                whatsapp_composer.with_user(user_id).with_delay()._send_whatsapp_template(
                    force_send_by_cron=force_send_by_cron
                )

    def send_whatsapp_template_from_discuss(self, wa_template_id, channel_id):
        wa_template = self.env["whatsapp.template"].browse(wa_template_id)
        channel = self.env["discuss.channel"].browse(channel_id)
        user_id = self.env.user.id
        _logger.info(
            "Sending WhatsApp template %s to channel %s with user %s",
            wa_template_id,
            channel_id,
            user_id,
        )
        whatsapp_composer = (
            self.env["whatsapp.composer"]
            .with_context(
                {
                    "active_model": wa_template.model,
                    "active_id": channel.whatsapp_partner_id.id,
                    "lang": channel.whatsapp_partner_id.lang,
                    "tz": "America/Bogota",
                    "uid": user_id,
                }
            )
            .with_user(user_id)
            .create(
                {
                    "phone": channel.whatsapp_number,
                    "wa_template_id": wa_template.id,
                    "res_model": wa_template.model,
                }
            )
        )
        whatsapp_composer.with_user(user_id)._send_whatsapp_template(
            force_send_by_cron=False
        )

    @api.onchange("category_id")
    def _onchange_category_id(self):
        for rec in self:
            channels = rec.env["discuss.channel"].search(
                [
                    ("whatsapp_partner_id", "=", rec.id),
                ]
            )
            for channel in channels:
                # Remove all categories from the channel
                channel.write({"partner_category_id": [(5, 0, 0)]})
                for cat in rec.category_id:
                    # Add the new categories to the channel
                    channel.write({"partner_category_id": [(4, cat.id)]})