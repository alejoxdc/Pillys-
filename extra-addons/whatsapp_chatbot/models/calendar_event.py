import logging
from odoo import api, fields, models, _,SUPERUSER_ID

_logger = logging.getLogger(__name__)

class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    def _send_template(self, wa_template):
        for rec in self:
            _logger.info("Sending WhatsApp template %s to %s", wa_template.name, rec.name)
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
                    .with_user(SUPERUSER_ID)
                    .create(
                        {
                            "phone": phone_number,
                            "wa_template_id": wa_template.id,
                            "res_model": wa_template.model_id.model,
                        }
                    )
                )
                whatsapp_composer.with_user(SUPERUSER_ID).with_delay()._send_whatsapp_template(
                    force_send_by_cron=False
                )