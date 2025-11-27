from odoo import api, fields, models, tools, _
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class wizard_multiple_test_request(models.TransientModel):
    _inherit = 'wizard.multiple.test.request'
    _description = "This is form for view of tender"

    owner_name = fields.Many2one('res.partner', 'Owner Name', required=True)

    _defaults = {
        'r_date': lambda *a: datetime.strftime('%Y-%m-%d %H:%M:%S'),

    }

    @api.onchange('patient_id')
    def onchange_patient(self):
        v = {}
        reg_pat1 = self.patient_id
        v['owner_name'] = reg_pat1.partner_id.owner_name.id
        return {'value': v}

    def create_lab_test(self):
        a = []
        result = {}
        test_request_obj = self.env['medical.patient.lab.test']
        lab_obj = self.env['medical.lab']

        test_report_data = {}
        test_cases = []
        q1 = self
        if q1.patient_id.partner_id.owner_name.id != q1.owner_name.id:
            raise UserError(_("Please select correct owner."))
        for test_obj1 in q1.tests_id:
            test_report_data = {}
            test_report_data['test'] = test_obj1.id
            test_report_data['patient_id'] = q1.patient_id.id
            test_report_data['doctor_id'] = q1.phy_id.id
            test_report_data['date'] = q1.r_date
            test_report_data['name'] = test_obj1.id
            test_report_data['state'] = 'tested'
            test_report_data['owner_name'] = q1.owner_name.id
            lab_id = test_request_obj.create(test_report_data)
            a.append(lab_id.id)

        for test_obj1 in q1.tests_id:
            test_report_data = {}
            test_report_data['test'] = test_obj1.id
            test_report_data['patient'] = q1.patient_id.id
            test_report_data['requestor'] = q1.phy_id.id
            test_report_data['date_requested'] = q1.r_date
            for critearea in test_obj1.critearea:
                test_cases.append((0, 0, {'name': critearea.name,
                                          'sequence': critearea.sequence,
                                          'normal_range': critearea.normal_range,
                                          'lower_limit': critearea.lower_limit,
                                          'upper_limit': critearea.upper_limit,
                                          'units': critearea.units.id,
                                          }))
            test_report_data['critearea'] = test_cases
            test_cases = []
            lab_id = lab_obj.create(test_report_data)

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
        if a:
            result['domain'] = "[('id','in',%s)]" % a
        return result
