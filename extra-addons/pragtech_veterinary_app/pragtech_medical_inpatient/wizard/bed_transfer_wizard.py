# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from datetime import datetime


class medical_bed_transfer_wizard(models.TransientModel):
    _name = 'medical.bed.transfer.wizard'
    _description = 'Create Bed Transfer Init'
    
    newbed = fields.Many2one('medical.hospital.bed', 'New Bed', required=True)
    reason = fields.Char('Reason', size=256, required=True)
    
    def bed_transfer(self):
        bed_transfer = self.env['bed.transfer']
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []
        if len(active_ids) > 1:
            raise UserError(_('You have chosen more than 1 records. Please choose only one.'))
        for record in self.env['medical.inpatient.registration'].browse(active_ids):
            if record.state not in ('confirmed', 'hospitalized'):
                raise UserError(_('Can not transfer bed if record is not in state of confirmed or hospitalized.'))
            if self.newbed.state == 'free':
                self.newbed.write({'state': 'occupied'})
                record.bed.write({'state': 'free'})
                vals = {
                    'transfer_date': datetime.now(),
                    'bed_from': record.bed.id,
                    'bed_to': self.newbed.id,
                    'reason': self.reason,
                    'name': record.id,
                }
                bed_transfer.create(vals)
                record.write({'bed': self.newbed.id})
            else:
                raise UserError(_('Selected new bed is not Free.'))
        return {'type': 'ir.actions.act_window_close'}

