# -*- coding: utf-8 -*-
from odoo import models

class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    def _channel_info(self):
        channel_infos = super()._channel_info()
        channel_infos_dict = {c['id']: c for c in channel_infos}
        action_id = self.env['ir.actions.actions'].sudo().search([('name', '=', 'Discuss Whatsapp')], limit=1)

        for channel in self:
            if channel.channel_type == 'whatsapp':
                channel_infos_dict[channel.id]['whatsapp_partner_name'] = channel.whatsapp_partner_id.name
                channel_infos_dict[channel.id]['whatsapp_partner_id'] = channel.whatsapp_partner_id.id
                channel_infos_dict[channel.id][
                    'whatsapp_partner_img_url'] = f"/web/image?model=res.partner&field=image_512&id={channel.whatsapp_partner_id.id}"
                if action_id.id:
                    channel_infos_dict[channel.id]['action_id_whatsapp'] = action_id.id
        return list(channel_infos_dict.values())

    def action_whatsapp(self):
        action_id = self.env['ir.actions.actions'].sudo().search([('name', '=', 'Discuss Whatsapp')], limit=1)
        if action_id:
            return action_id.id
