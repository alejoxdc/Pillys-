# coding=utf-8

#    Copyright (C) 2008-2010  Luis Falcon

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.


from odoo import api, fields, models, tools, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class medical_rcri(models.Model):
    _name = "medical.rcri"
    _description = "Revised Cardiac Risk Index"

    patient_id = fields.Many2one('medical.patient', 'Patient', required=True, )
    #         name = fields.Char('name',)
    rcri_date = fields.Datetime('RCRI Date', default=fields.Datetime.now)
    surgeon = fields.Many2one('medical.physician', 'Health professional',
                              help="Health professional/Cardiologist who signed the assesment RCRI")
    rcri_high_risk_surgery = fields.Boolean('High Risk surgery',
                                            help='Includes andy suprainguinal vascular, intraperitoneal, or intrathoracic procedures')
    rcri_ischemic_history = fields.Boolean('History of ischemic heart disease',
                                           help='history of MI or a positive exercise test, current complaint of chest pain considered to be secondary to myocardial \
        ischemia, use of nitrate therapy, or ECG with pathological Q waves; do not count prior coronary revascularization procedure \
        unless one of the other criteria for ischemic heart disease is present')
    rcri_congestive_history = fields.Boolean('History of congestive heart disease', )
    rcri_diabetes_history = fields.Boolean('Preoperative Diabetes',
                                           help="Diabetes Mellitus requiring treatment with Insulin")
    rcri_cerebrovascular_history = fields.Boolean('History of Cerebrovascular disease', )
    rcri_kidney_history = fields.Boolean('Preoperative Kidney disease',
                                         help='Preoperative serum creatinine >2.0 mg/dL (177 mol/L)')
    rcri_total = fields.Integer('Score',
                                help='Points 0: Class I Very Low (0.4% complications)\n'
                                     'Points 1: Class II Low (0.9% complications)\n'
                                     'Points 2: Class III Moderate (6.6% complications)\n'
                                     'Points 3 or more : Class IV High (>11% complications)')
    rcri_class = fields.Selection([
        ('I', 'I'),
        ('II', 'II'),
        ('III', 'III'),
        ('IV', 'IV'),
    ], 'RCRI Class', default='I')

    @api.onchange('rcri_high_risk_surgery', 'rcri_ischemic_history', 'rcri_congestive_history', 'rcri_diabetes_history',
                  'rcri_kidney_history', 'rcri_cerebrovascular_history')
    def onchange_of_rcri_total(self):
        total = 0
        rcri_class = None
        if self.rcri_high_risk_surgery:
            total += 1
        if self.rcri_ischemic_history:
            total += 1
        if self.rcri_congestive_history:
            total += 1
        if self.rcri_diabetes_history:
            total += 1
        if self.rcri_kidney_history:
            total += 1
        if self.rcri_cerebrovascular_history:
            total += 1
        if total == 0:
            rcri_class = 'I'
        if total == 1:
            rcri_class = 'II'
        if total == 2:
            rcri_class = 'III'
        if (total > 2):
            rcri_class = 'IV'
        self.rcri_total = total
        self.rcri_class = rcri_class


#     def name_get(self, cr, uid, ids, context):
#         res = []
#         if not len(ids):
#             return res
#         for r in self.read(cr, uid, ids, ['rcri_total','rcri_class']):
#             addr = 'Points: '
#             addr += str(r['rcri_total'] or '')
#             addr += '  (Class'
#             addr += (r['rcri_class'] or '') + ')'
#             res.append((r['id'], addr))
#              
#         return res


class surgery(models.Model):
    _name = "medical.surgery"
    _description = "Surgery"

    def surgery_duration(self):
        def compute_age_from_dates(surgery_end, surgery_date):
            now = datetime.now()
            if (surgery_end and surgery_date):
                dob = datetime.strptime(str(surgery_end), '%Y-%m-%d %H:%M:%S')
                surgery_date = datetime.strptime(str(surgery_date), '%Y-%m-%d %H:%M:%S')
                delta = relativedelta(dob, surgery_date)
                years_months_days = str(delta.days * 24 + delta.hours) + "h " + str(delta.months) + "m "
            else:
                years_months_days = "No Start/End !"

            return years_months_days

        result = {}
        for patient_data in self:
            result[patient_data.id] = compute_age_from_dates(patient_data.surgery_end_date, patient_data.date)
            surgery_length = compute_age_from_dates(patient_data.surgery_end_date, patient_data.date)
        self.surgery_length = surgery_length
        return result

    # @api.depends('patient_id.dob', 'date')
    # def _patient_age(self):
    #     def compute_age_from_dates(patient_dob, surgery_date):
    #         now = datetime.now()
    #         if (patient_dob):
    #             dob = datetime.strptime(str(patient_dob), '%Y-%m-%d')
    #         #                 if (surgery_date):
    #         #                     surgery_date=datetime.today().strptime(str(surgery_date),'%Y-%m-%d')
    #         #                     delta=relativedelta (surgery_date, dob)
    #         #                     years_months_days = str(delta.years) +"y "+ str(delta.months) +"m "+ str(delta.days)+"d"
    #         #                 else:
    #         #                     years_months_days = "No Surgery Date !"

    #         else:
    #             years_months_days = "No DoB !"
    #             return years_months_days

        # result = {}

        # for patient_data in self:
        #     result[patient_data.id] = compute_age_from_dates(patient_data.patient_id.dob, patient_data.date)
        #     year = compute_age_from_dates(patient_data.patient_id.dob, patient_data.date)
        # self.surgery_age = year

    patient_id = fields.Many2one('medical.patient', 'Patient', required=True, )
    name = fields.Char('Code', required=True, help="Health Center Unique code")
    pathology = fields.Many2one('medical.pathology', 'Base condition', help="Base Condition / Reason")
    classification = fields.Selection([
        ('o', 'Optional'),
        ('r', 'Required'),
        ('u', 'Urgent'),
        ('e', 'Emergency'),
    ], 'Surgery Classification', index=True)
    surgeon = fields.Many2one('medical.physician', 'Surgeon', help="Surgeon who did the procedure")
    date = fields.Datetime('Date of the surgery')
    surgery_end_date = fields.Datetime('End of the surgery')
    surgery_length = fields.Char(compute='surgery_duration', string='Duration',
                                 help='Patient age at the moment of the surgery. Can be estimative')
    surgery_age = fields.Char(related='patient_id.age', string='Patient Age',
                              help='Patient age at the moment of the surgery. Can be estimative')
    #         'age'= fields.Char ('Patient age',size=3,help='Patient age at the moment of the surgery. Can be estimative')
    description = fields.Char('Description', size=128)
    extra_info = fields.Text('Details/Incidents')
    anesthesia_report = fields.Text('Anesthesia Report')
    operating_room = fields.Many2one('medical.hospital.oprating.room', 'Operating Room')
    procedures = fields.One2many('medical.operation', 'name', 'Procedures',
                                 help="List of the procedures in the surgery. Please enter the first one as the main procedure")
    anesthetist = fields.Many2one('medical.physician', 'Anesthetist', help="Anesthetist in charge")
    signed_by = fields.Many2one('medical.physician', 'Signed by',
                                help="Health Professional that signed this surgery document")
    preop_asa = fields.Selection([
        ('ps1', 'PS 1 : Normal healthy patient'),
        ('ps2', 'PS 2 : Patients with mild systemic disease'),
        ('ps3', 'PS 3 : Patients with severe systemic disease'),
        ('ps4', 'PS 4 : Patients with severe systemic disease that is'
                ' a constant threat to life '),
        ('ps5', 'PS 5 : Moribund patients who are not expected to'
                ' survive without the operation'),
        ('ps6', 'PS 6 : A declared brain-dead patient who organs are'
                ' being removed for donor purposes'),
    ], 'ASA PS', help="ASA pre-operative Physical Status", )

    preop_mallampati = fields.Selection([
        ('Class 1', 'Class 1: Full visibility of tonsils, uvula and soft '
                    'palate'),
        ('Class 2', 'Class 2: Visibility of hard and soft palate, '
                    'upper portion of tonsils and uvula'),
        ('Class 3', 'Class 3: Soft and hard palate and base of the uvula are '
                    'visible'),
        ('Class 4', 'Class 4: Only Hard Palate visible')
    ], 'Mallampati Score')

    preop_bleeding_risk = fields.Boolean('Risk of Massive bleeding',
                                         help="Check this box if patient has a risk of loosing more than 500 "
                                              "ml in adults of over 7ml/kg in infants. If so, make sure that "
                                              "intravenous access and fluids are available")
    preop_oximeter = fields.Boolean('Pulse Oximeter in place',
                                    help="Check this box when verified the pulse oximeter is in place "
                                         "and functioning")
    preop_site_marking = fields.Boolean('Surgical Site Marking',
                                        help="The surgeon has marked the surgical incision")
    preop_antibiotics = fields.Boolean('Antibiotic Prophylaxis',
                                       help="Prophylactic antibiotic treatment within the last 60 minutes")
    preop_sterility = fields.Boolean('Sterility confirmed',
                                     help="Nursing team has confirmed sterility of the devices and room")
    preop_rcri = fields.Many2one('medical.rcri', 'RCRI',
                                 help='Patient Revised Cardiac Risk Index\n'
                                      'Points 0: Class I Very Low (0.4% complications)\n'
                                      'Points 1: Class II Low (0.9% complications)\n'
                                      'Points 2: Class III Moderate (6.6% complications)\n'
                                      'Points 3 or more : Class IV High (>11% complications)')
    state = fields.Selection([
        ('in_progress', 'In progress'),
        ('done', 'Done'),
    ], 'State', readonly=True, default='in_progress')

    def done(self):
        self.write({'state': 'done'})
        return True


# Add to the Medical patient_data class (medical.patient) the surgery field.

class medical_patient(models.Model):
    _name = "medical.patient"
    _inherit = "medical.patient"

    surgery_ids = fields.One2many('medical.surgery', 'patient_id', 'Surgeries')


#         'surgery' : fields.many2many ('medical.surgery', 'patient_surgery_rel','patient_id','surgery_id', 'Surgeries')


class medical_operation(models.Model):
    _name = "medical.operation"

    name = fields.Many2one('medical.surgery', 'Surgery')
    procedure = fields.Many2one('medical.procedure', 'Code',
                                help="Procedure Code, for example ICD-10-PCS Code 7-character string")
    notes = fields.Text('Notes')
