import logging
from odoo import api, fields, models, SUPERUSER_ID, _
from datetime import datetime, time, timedelta
from dateutil import tz

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = "crm.lead"

    # def assign_campaign(self, identification_code, social_network):
    #     Ad = self.env['utm.campaign.ad']  # replace 'ad.model' with the actual name of the related model
    #     ad_ids = Ad.search([('name', '=', identification_code)]).ids
    #     campaign = self.env["utm.campaign"].search(
    #         [
    #             '|',
    #             ("meta_id_campaign", "=", identification_code),
    #             ("ad_ids", "in", ad_ids),
    #         ],
    #         limit=1,
    #     )
    #     _logger.info("Campaign asignation")
    #     _logger.info("Campaign found: %s", campaign)
    #     if campaign:
    #         # search for media with the same name as the social network
    #         media = self.env["utm.medium"].search([("name", "=", social_network)], limit=1)
    #         if media:
    #             self.medium_id = media.id
    #         else:
    #             # if the media doesn't exist, create it
    #             self.medium_id = self.env["utm.medium"].create(
    #                 {"name": social_network}
    #             ).id
    #         # search for origin with the same name as the social network
    #         origin = self.env["utm.source"].search([("name", "=", social_network)], limit=1)
    #         if origin:
    #             self.source_id = origin.id
    #         else:
    #             # if the origin doesn't exist, create it
    #             self.source_id = self.env["utm.source"].create(
    #                 {"name": social_network}
    #             ).id
    #         self.campaign_id = campaign.id

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

    def send_message_to_recent_opportunities(self):
        # Get the current date and time in the 'America/Bogota' timezone
        bogota_tz = tz.gettz('America/Bogota')
        now = datetime.now(tz=bogota_tz)

        # Calculate the start and end times for the range
        end_time = datetime.combine(now.date(), time(8, 59), tzinfo=bogota_tz)
        start_time = end_time - timedelta(hours=18)

        # Fetch opportunities that arrived within the time range
        opportunities = self.env['crm.lead'].search([
            ('create_date', '>=', start_time),
            ('create_date', '<=', end_time)
        ])

        # Send template to each opportunity
        for opportunity in opportunities:
            opportunity._send_template(196)


    def get_crm_stages(self):
        stages = self.env["crm.stage"].search([])
        stages_list = []

        for stage in stages:
            stages_list.append({
                "id": stage.id,
                "name": stage.name,
                "is_won": stage.is_won,
                "team_id": stage.team_id.id,
            })

        return stages_list