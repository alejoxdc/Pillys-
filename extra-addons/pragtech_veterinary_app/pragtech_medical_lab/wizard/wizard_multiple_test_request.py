# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
import time


class WizardMultipleTestRequest(models.TransientModel):
    _name = 'wizard.multiple.test.request'
    _description = "This is form for view of tender"

    phy_id = fields.Many2one("medical.physician", 'Doctor', required=True)
    patient_id = fields.Many2one('medical.patient', 'Patient', required=True, index=True)
    r_date = fields.Date('Request Date', required=True, default=fields.Date.context_today)
    urgent = fields.Boolean('Urgent')
    tests_id = fields.Many2many('medical.test_type', 'multi_test_rel', 'test_id', 'wiz_id', "Test List")

    def create_lab_test(self):
        test_request_obj = self.env['medical.patient.lab.test']
        lab_obj = self.env['medical.lab']

        test_report_data = {}
        test_cases = []
        a_list = []
        for test_obj1 in self.tests_id:
            test_report_data['test'] = test_obj1.id
            test_report_data['patient_id'] = self.patient_id.id
            test_report_data['doctor_id'] = self.phy_id.id
            test_report_data['date'] = self.r_date
            test_report_data['name'] = test_obj1.id
            test_report_data['state'] = 'tested'
            lab_id = test_request_obj.create(test_report_data)
            lab_id.write({'state': 'tested'})
            a_list.append(lab_id.id)

        for test_obj1 in self.tests_id:
            test_report_list = {}
            test_report_list['test'] = test_obj1.id
            test_report_list['patient'] = self.patient_id.id
            test_report_list['requestor'] = self.phy_id.id
            test_report_list['date_requested'] = self.r_date

            for critearea in test_obj1.critearea:
                test_cases.append((0, 0, {'name': critearea.name,
                                          'sequence': critearea.sequence,
                                          'normal_range': critearea.normal_range,
                                          'lower_limit': critearea.lower_limit,
                                          'upper_limit': critearea.upper_limit,
                                          'units': critearea.units.id,
                                          }))
            test_report_list['critearea'] = test_cases
            test_cases = []
            lab_id = lab_obj.create(test_report_list)

        imd = self.env['ir.model.data']
        list_view_id = imd._xmlid_to_res_id('medical_lab_test_request_tree')
        form_view_id = imd._xmlid_to_res_id('medical_lab_test_request_form')

        result = {
            'name': 'Lab Multiple Test Report',
            'type': 'tree',
            'target': 'current',
            'views': [[list_view_id, 'tree'], [form_view_id, 'form']],
            'res_model': 'medical.patient.lab.test',
            'type': 'ir.actions.act_window',
        }
        if a_list:
            result['domain'] = "[('id','in',%s)]" % a_list
        return result
