# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError


class MedicalImagingTesRequestWizard(models.TransientModel):
    _name = 'medical.imaging.test.request.wizard'
    
    @api.model
    def _get_default_doctor(self):
        doc_ids = None
        partner_ids = self.env['res.partner'].search([('user_id', '=', self.env.user.id), ('is_doctor', '=', True)])
        if partner_ids:
            doc_ids = self.env['medical.physician'].search([('name', 'in', partner_ids)])
            if doc_ids:
                return doc_ids.id
        return doc_ids
    
    patient_id = fields.Many2one('medical.patient', 'Patient')
    test_date = fields.Datetime('Test Date', default=fields.Datetime.now)
    physician_id = fields.Many2one('medical.physician', 'Physician', default=_get_default_doctor)
    test_ids = fields.Many2many('medical.imaging.test', 'imaging_test_request_wizard_id', 'test_id', 'wizard_id', 'Test')
    urgent = fields.Boolean('Urgent')
    
    def create_imaging_request(self):
        image_request = self.env['medical.imaging.test.request']
        test_id_list = []
        for test in self.test_ids:
            vals = {
                'patient_id': self.patient_id.id,
                'test_date': self.test_date,
                'physician_id': self.physician_id.id,
                'urgent': self.urgent,
                'test_id': test.id,
            }
            test_id = image_request.create(vals)
            test_id_list.append(test_id.id)
        imd = self.env['ir.model.data']
        res_id = imd._xmlid_to_res_id('medical_imaging_test_request_tree')
        res_id_form = imd._xmlid_to_res_id('medical_imaging_test_request_form')
        
        result = {
            'name': 'Imaging Request',
            'type': 'tree',
            'views': [(res_id, 'tree'),(res_id_form, 'form')],
            'target': 'current',
            'res_model': 'medical.imaging.test.request',
            'type': 'ir.actions.act_window',
        }
        if test_id_list:
            result['domain'] = "[('id','in',%s)]" % test_id_list
        return result
