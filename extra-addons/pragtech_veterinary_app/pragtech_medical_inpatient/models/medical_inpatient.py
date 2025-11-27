# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from datetime import datetime
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class MedicalInpatientMedication (models.Model):
    _name = "medical.inpatient.medication"


class MedicalInpatientRegistration (models.Model):
    _name = "medical.inpatient.registration" 
    _description = "Patient admission History"
    
    name = fields.Char('Registration Code', size=128, readonly=True)
    patient = fields.Many2one('medical.patient', 'Patient', required=True)
    admission_type = fields.Selection([
        ('routine', 'Routine'),
        ('maternity', 'Maternity'),
        ('elective', 'Elective'),
        ('urgent', 'Urgent'),
        ('emergency', 'Emergency')], 'Admission type', required=True)
    hospitalization_date = fields.Datetime('Hospitalization date', required=True)
    discharge_date = fields.Datetime('Expected Discharge date', required=True)
    attending_physician = fields.Many2one('medical.physician', 'Attending Physician')
    operating_physician = fields.Many2one('medical.physician', 'Operating Physician')
    admission_reason = fields.Many2one('medical.pathology', 'Reason for Admission', help="Reason for Admission")
    bed = fields.Many2one('medical.hospital.bed', 'Hospital Bed', required=True)
    nursing_plan = fields.Text('Nursing Plan')
    discharge_plan = fields.Text('Discharge Plan')
    info = fields.Text('Extra Info')
    state = fields.Selection([
        ('free', 'free'),
        ('cancelled', 'cancelled'),
        ('confirmed', 'confirmed'),
        ('hospitalized', 'hospitalized')], 'Status', default='free')
    bed_transfers = fields.One2many('bed.transfer', 'name', 'Transfer History')
    diet_belief = fields.Many2one('medical.diet.belief', 'Diet Belief', help="Enter the patient belief or religion to choose the proper diet")
    diet_vegetarian = fields.Selection([
        ('vegetarian', 'Vegetarian'),
        ('lacto', 'Lacto vegetarian'),
        ('lactoovo', 'Lacto-ovo vegetarian'),
        ('pescetarian', 'Pescetarian'),
        ('vegan', 'Vegan')], 'Diet Type', required=True)
    nutrition_notes = fields.Text('Nutrition notes / directions')
    therapeutic_diets = fields.One2many('medical.inpatient.diet', 'name', 'Therapeutic Diets')
    medications = fields.One2many('medical.inpatient.medication', 'name', 'Medications')
    
    _sql_constraints = [
                ('name_uniq', 'unique (name)', 'The Registration code already exists'),
                ('hospitalization_dates', 'CHECK (hospitalization_date<=discharge_date)',  'Hospitalization Date Should be lesser than the Discharge Date!'),]
    
    def registration_confirm(self):
        for reservation in self:
            bed_id= str(reservation.bed.id)
            self._cr.execute("select count (*) from medical_inpatient_registration where (hospitalization_date::timestamp,discharge_date::timestamp) overlaps ( timestamp %s , timestamp %s ) and state= %s and bed = cast(%s as integer)", (reservation.hospitalization_date,reservation.discharge_date,'confirmed',bed_id))
            res = self._cr.fetchone()
            if res and res[0]:
                raise ValidationError(_('Bed has been already reserved in this period.'))
            else:
                reservation.bed.write({'state': 'reserved'})
        self.write({'state': 'confirmed'})
   
    def patient_discharge(self):
        for reservation in self:
            reservation.bed.write({'state': 'free'})
        self.write({'state': 'free'})
       
    def registration_cancel(self):
        for reservation in self:
            reservation.bed.write({'state': 'free'})
        self.write({'state': 'cancelled'})
       
    def registration_admission(self):
        for reservation in self:
            reservation.bed.write({'state': 'occupied'})
        self.write({'state': 'hospitalized'})
       
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('medical.inpatient.registration') or 'New'
    
        result = super(MedicalInpatientRegistration, self).create(vals)
        return result


class MedicalInpatientMedicationAdminTime(models.Model):
    _name = "medical.inpatient.medication.admin.time"
    _description = 'Inpatient Medication Admin Times'
    
    @api.model
    def _get_default_doctor(self):
        doc_ids = None
        partner_ids = self.env['res.partner'].search([('user_id', '=', self.env.user.id), ('is_doctor', '=', True)])
        if partner_ids:
            doc_ids = self.env['medical.physician'].search([('res_partner_physician_id', 'in', partner_ids.ids)])
            if doc_ids:
                return doc_ids.id
        return doc_ids
    
    name = fields.Many2one('medical.inpatient.medication', 'Medication')
    admin_time = fields.Datetime("Date", default=fields.Datetime.now)
    health_professional = fields.Many2one('medical.physician', 'Health Professional', default=_get_default_doctor)
    dose = fields.Float('Dose', help='Amount of medication (eg, 250 mg) per dose')
    dose_unit = fields.Many2one('medical.dose.unit', 'dose unit', help='Unit of measure for the medication to be taken')
    remarks = fields.Text('Remarks', help='specific remarks for this dose')


class MedicalInpatientMedication (models.Model):
    _inherit = "medical.inpatient.medication"
    _inherits = {'medical.medication.template' : 'medication_id'}
    _description = "Inpatient Medication"
    
    medication_id = fields.Many2one('medical.medication.template', 'medication_id', required=True, ondelete='cascade')
    name = fields.Many2one('medical.inpatient.registration', 'Registration Code')
    is_active = fields.Boolean('Active', default=True, help="Check this option if the patient is currently taking the medication")
    discontinued = fields.Boolean('Discontinued')
    course_completed = fields.Boolean('Course Completed')
    discontinued_reason = fields.Char('Reason for discontinuation', size=128, help="Short description for discontinuing the treatment")
    adverse_reaction = fields.Text('Adverse Reactions / Notes', help="Specific side effects or adverse reactions that the patient experienced")
    log_history = fields.One2many('medical.inpatient.medication.log', 'name', "Log History")
    admin_times = fields.One2many('medical.inpatient.medication.admin.time', 'name', "Admin times")
    
    @api.onchange('course_completed', 'discontinued', 'is_active')
    def onchange_course_completed(self):
        if self.course_completed:
            self.is_active = False
            self.discontinued = False
        elif self.is_active == False and self.discontinued == False and self.course_completed == False:
            self.is_active = True
        if self.discontinued == True:
            self.is_active = False
            self.course_completed = False
        elif self.is_active == False and self.discontinued == False and self.course_completed == False:
            self.is_active = True
        if self.is_active == True:
            self.discontinued = False
            self.course_completed = False
        elif self.is_active == False and self.discontinued == False and self.course_completed == False:
            self.course_completed = True


class MedicalAppointment (models.Model):
    _inherit = "medical.appointment"
    
    inpatient_registration_code = fields.Many2one('medical.inpatient.registration', 'Inpatient Registration', help="Enter the patient hospitalization code")
    
    @api.onchange('patient', 'patient_status')
    def onchange_patient(self):
        domain_list = []
        domain = {}
        if self.patient_status == 'inpatient':
            res_id = self.env['medical.inpatient.registration'].search([('patient.id', '=', self.patient.id)])
            if res_id:
                self.inpatient_registration_code = res_id.id
            else:
                self.inpatient_registration_code = ''
            res_id_list = self.env['medical.inpatient.registration'].search([('state', '=', 'hospitalized')])
            for res in res_id_list:
                domain_list.append(res.patient.id)  
        if self.patient_status == 'outpatient':
            res_id_list = self.env['medical.inpatient.registration'].search([('state', '=', 'hospitalized')])
            new_domain_list = []
            for res in res_id_list:
                new_domain_list.append(res.patient.id) 
            patient_ids = self.env['medical.patient'].search([('id', 'not in', new_domain_list)])
            for patient in patient_ids:
                domain_list.append(patient.id) 
        domain['patient'] = [('id', 'in', domain_list)]
        return {'domain': domain}
                

class MedicalDietBelief (models.Model):
    _name = "medical.diet.belief"
    
    name = fields.Char('Belief', required=True, translate=True)
    code = fields.Char('Code', required=True)
    description = fields.Text('Description', required=True, translate=True)
    
    _sql_constraints = [('code_uniq', 'unique (code)', 'The Diet code already exists')]


class MedicalDietTherapeutic (models.Model):
    _name = "medical.diet.therapeutic"
    
    name = fields.Char('Diet type', required=True, translate=True)
    code = fields.Char('Code', required=True)
    description = fields.Text('Description', required=True, translate=True)

    _sql_constraints = [('code_uniq', 'unique (code)', 'The Diet therapeutic code already exists')]


class MedicalInpatientDiet(models.Model):
    _name = "medical.inpatient.diet"
    
    name = fields.Many2one('medical.inpatient.registration', 'Registration Code')
    diet = fields.Many2one('medical.diet.therapeutic', 'Diet', required=True)
    remarks = fields.Text('Remarks / Directions', help='specific remarks for this diet / patient')


class MedicalInpatientMedicationLog(models.Model):
    _name = "medical.inpatient.medication.log"
    _description = "Inpatient Medication Log History"
    
    @api.model
    def _get_default_doctor(self):
        doc_ids = None
        partner_ids = self.env['res.partner'].search([('user_id', '=', self.env.user.id), ('is_doctor', '=', True)])
        if partner_ids:
            doc_ids = self.env['medical.physician'].search([('res_partner_physician_id', 'in', partner_ids.ids)])
            if doc_ids:
                return doc_ids.id
        return doc_ids
    
    name = fields.Many2one('medical.inpatient.medication', 'Medication')
    admin_time = fields.Datetime("Date", readonly=True, default=fields.Datetime.now)
    health_professional = fields.Many2one('medical.physician', 'Health Professional', readonly=True, default=_get_default_doctor)
    dose = fields.Float('Dose', help='Amount of medication (eg, 250 mg) per dose')
    dose_unit = fields.Many2one('medical.dose.unit', 'dose unit', help='Unit of measure for the medication to be taken')
    remarks = fields.Text('Remarks', help='specific remarks for this dose')


class BedTransfer(models.Model):
    _name = "bed.transfer"
     
    name = fields.Many2one('medical.inpatient.registration', 'Registration Code')
    transfer_date = fields.Datetime('Date')
    bed_from = fields.Many2one('medical.hospital.bed', 'From', )
    bed_to = fields.Many2one('medical.hospital.bed', 'To',)
    reason = fields.Char('Reason')


# Add the patient status to the partner
class MedicalPatient(models.Model):
    _inherit = "medical.patient"
    _description = "Patient related information"
    
    # patient_status = fields.Char('Hospitalization Status',related ='patient_id.id')
    patient_status = fields.Char('Hspitalization Status', compute='_get_patient_status', help="Shows whether the patient is hospitalized")
    
    def _get_patient_status (self):
        for rec in self:
            rec.patient_status = False
#         def get_hospitalization_status(patient_dbid):
#             self._cr.execute ( 'select state from medical_inpatient_registration where patient=%s and state=\'hospitalized\'', (patient_dbid,))  
#             try:
#                 patient_status = str(self._cr.fetchone()[0])
#             except:
#                 patient_status = "outpatient"
#   
#             return patient_status
#         if len(self._origin) >= 1:
#             self.patient_status = get_hospitalization_status(self.id)
