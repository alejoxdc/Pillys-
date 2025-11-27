# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, RedirectWarning, ValidationError


# Add Lab test information to the Patient object

class MedicalPatient(models.Model):
    _name = "medical.patient"
    _inherit = "medical.patient"

    lab_test_ids = fields.One2many('medical.patient.lab.test', 'patient_id', 'Lab Tests Required', readonly=True)


class MedicalTestType(models.Model):
    _name = "medical.test_type"
    _description = "Type of Lab test"

    name = fields.Char('Test', size=128, help="Test type, eg X-Ray, hemogram,biopsy...", required=True)
    code = fields.Char('Code', size=128, help="Short name - code for the test", required=True)
    info = fields.Text('Description')
    product_id = fields.Many2one('product.product', 'Service', required=True)
    critearea = fields.One2many('medical_test.critearea', 'test_type_id', 'Test Cases')

    sql_constraints = [
        ('code_uniq', 'unique (name)', 'The Lab Test code must be unique')]


class MedicalLab(models.Model):
    _name = "medical.lab"
    _description = "Lab Test"
    _order = "name desc"

    name = fields.Char('ID', size=128, help="Lab result ID", readonly=True, default=lambda self: _('New'))
    test = fields.Many2one('medical.test_type', 'Test type', help="Lab test type", required=True, )
    patient = fields.Many2one('medical.patient', 'Patient', help="Patient ID", required=True, )
    pathologist = fields.Many2one('medical.physician', 'Pathologist', help="Pathologist")
    requestor = fields.Many2one('medical.physician', 'Physician', help="Doctor who requested the test")
    results = fields.Text('Results')
    diagnosis = fields.Text('Diagnosis')
    critearea = fields.One2many('medical_test.critearea', 'medical_lab_id', 'Test Cases')
    date_requested = fields.Datetime('Date requested', required=True, default=fields.Datetime.now)
    date_analysis = fields.Datetime('Date of the Analysis', default=fields.Datetime.now)

    _sql_constraints = [
        ('id_uniq', 'unique (name)', 'The test ID code must be unique')]

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('medical.lab') or 'New'
        result = super(MedicalLab, self).create(vals)
        return result


class MedicalLabTestUnits(models.Model):
    _name = "medical.lab.test.units"

    name = fields.Char('Unit', size=25)
    code = fields.Char('Code', size=25)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'The Unit name must be unique')]


class MedicalTestCritearea(models.Model):
    _name = "medical_test.critearea"
    _description = "Lab Test Critearea"
    _order = "sequence"

    name = fields.Char('Test', size=64, required=True)
    result = fields.Float('Result')
    normal_range = fields.Text('Normal Range')
    warning = fields.Boolean('Warning', default=False)
    excluded = fields.Boolean('Excluded', default=False)
    lower_limit = fields.Float('Lower Limit')
    upper_limit = fields.Float('Upper Limit')
    remark = fields.Text('Remark')
    result_text = fields.Char('Result - Text',
                              help='Non-numeric results. For example qualitative values, morphological, colors ...')
    units = fields.Many2one('medical.lab.test.units', 'Units')
    test_type_id = fields.Many2one('medical.test_type', 'Test type')
    medical_lab_id = fields.Many2one('medical.lab', 'Test Cases')
    sequence = fields.Integer('Sequence', default=1)

    @api.onchange('lower_limit', 'upper_limit', 'result')
    def onchange_result(self):
        if (float(self.result) < self.lower_limit or float(self.result) > self.upper_limit):
            self.warning = True
        else:
            self.warning = False


class MedicalPatientLabTest(models.Model):
    _name = 'medical.patient.lab.test'

    @api.model
    def _get_default_doctor(self):
        doc_ids = None
        partner_ids = self.env['res.partner'].search([('user_id', '=', self.env.user.id), ('is_doctor', '=', True)])
        if partner_ids:
            doc_ids = self.env['medical.physician'].search([('res_partner_physician_id', 'in', partner_ids.ids)])
        return doc_ids

    name = fields.Many2one('medical.test_type', 'Test Type')
    date = fields.Datetime('Date', default=fields.Datetime.now)
    state = fields.Selection([('draft', 'Draft'), ('tested', 'Tested'), ('cancel', 'Cancel')], 'State', readonly=True,
                             default='draft')
    patient_id = fields.Many2one('medical.patient', 'Patient', required=True, )
    doctor_id = fields.Many2one('medical.physician', 'Doctor', help="Doctor who Request the lab test.",
                                default=_get_default_doctor)
    request = fields.Char('Request', readonly=True, default=lambda self: _('New'))
    urgent = fields.Boolean('Urgent')

    @api.model
    def create(self, vals):
        if vals.get('request', 'New') == 'New':
            vals['request'] = self.env['ir.sequence'].next_by_code('medical.patient.lab.test') or 'New'
        result = super(MedicalPatientLabTest, self).create(vals)
        return result

    def create_lab_test(self):
        test_report_data = {}
        test_cases = []
        lab_id_list = []
        lab_obj = self.env['medical.lab']
        for test in self:
            if test.state == 'tested':
                raise ValidationError(_('At least one of the selected record Test Record is already created.'))
        for test in self:
            test_report_data['test'] = test.name.id
            test_report_data['patient'] = test.patient_id.id
            test_report_data['requestor'] = test.doctor_id.id
            test_report_data['date_requested'] = test.date
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
        self.write({'state': 'tested'})
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
