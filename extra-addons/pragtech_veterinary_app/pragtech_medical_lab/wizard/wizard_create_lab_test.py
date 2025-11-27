# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError


class MedicalLabTestCreate(models.TransientModel):
    _name = 'medical.lab.test.create'

    def create_lab_test(self):
        test_request_obj = self.env['medical.patient.lab.test']
        lab_obj = self.env['medical.lab']
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []
        result = {}

        for test in test_request_obj.browse(active_ids):
            if test.state == 'tested':
                raise UserError(_('At least one of the selected record Test Record is already created.'))

        lab_id_list = []

        for test in test_request_obj.browse(active_ids):
            test_report_data = {}
            test_report_data['test'] = test.name.id
            test_report_data['patient'] = test.patient_id.id
            test_report_data['requestor'] = test.doctor_id.id
            test_report_data['date_requested'] = test.date
            test_cases = []
            for critearea in test.name.critearea:
                test_cases.append((0, 0, {'name': critearea.name,
                                          'sequence': critearea.sequence,
                                          'normal_range': critearea.normal_range,
                                          'lower_limit': critearea.lower_limit,
                                          'upper_limit': critearea.upper_limit,
                                          'units': critearea.units.id,
                                          }))
                test_report_data['critearea'] = test_cases
            lab_id = lab_obj.create(test_report_data)
            lab_id_list.append(lab_id.id)
            test.write({'state': 'tested'})
        imd = self.env['ir.model.data']
        list_view_id = imd._xmlid_to_res_id('medical_lab_tree')
        form_view_id = imd._xmlid_to_res_id('medical_lab_view')
        result = {
            'name': 'Lab Test Report',
            'type': 'tree',
            'target': 'current',
            'views': [[list_view_id, 'tree'], [form_view_id, 'form']],
            'res_model': 'medical.lab',
            'type': 'ir.actions.act_window',
        }
        if lab_id_list:
            result['domain'] = "[('id','in',%s)]" % lab_id_list
        return result
