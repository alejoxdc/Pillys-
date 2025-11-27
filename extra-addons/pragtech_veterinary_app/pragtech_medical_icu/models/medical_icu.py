# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class MedicalInpatientRegistration(models.Model):
    _inherit = "medical.inpatient.registration"
    _description = "Patient admission History"
    
    icu = fields.Boolean('ICU', help='Shows if patient was admitted to the Intensive Care Unit during the hospitalization period')
    icu_admissions = fields.One2many('medical.inpatient.icu', 'name', "ICU Admissions")
    

class MedicalInpatientIcu(models.Model):
    _name = "medical.inpatient.icu"
    _description = 'Patient ICU Information'

    def icu_duration_time(self):
        now = datetime.now()
        for obj in self:
            admission = obj.icu_admission_date
            # admission = datetime.strptime(str(obj.icu_admission_date), '%Y-%m-%d %H:%M:%S')
            if obj.discharged_from_icu:
                disccharge = obj.icu_discharge_date
                # discharge = datetime.strptime(str(obj.icu_discharge_date), '%Y-%m-%d %H:%M:%S')
                delta = relativedelta(disccharge, admission)
            else:
                delta = relativedelta(now, admission)
            years_months_days = str(delta.years) + 'y ' \
                    + str(delta.months) + 'm ' \
                    + str(delta.days) + 'd ' \
                    + str(delta.hours) + 'h ' + str(delta.minutes) + 'mints '
            obj.icu_stay = years_months_days
    
    @api.constrains('name')
    def _check_currency_and_amount(self):
        self._cr.execute('select count(name) from medical_inpatient_icu where name = {0} and admitted '.format(self.name.id))
        if self._cr.fetchone()[0] > 1:
            raise ValidationError(_("Our records indicate that the patient is already admitted at ICU."))
     
    name = fields.Many2one('medical.inpatient.registration', 'Registration Code', required=True)
    admitted = fields.Boolean('Admitted', default=True, help="Will be set when the patient is currently admitted at ICU")
    icu_admission_date = fields.Datetime('ICU Admission', help="ICU Admission Date", required=True)
    discharged_from_icu = fields.Boolean('Discharged')
    icu_discharge_date = fields.Datetime('Discharge')
    icu_stay = fields.Char("Duration", size=128, store=True, compute='icu_duration_time')
    mv_history = fields.One2many('medical.icu.ventilation', 'name', "Mechanical Ventilation History")

    @api.onchange('admitted', 'discharged_from_icu')
    def onchange_with_descharge(self):
        if self.discharged_from_icu == False:
            self.admitted = True
        if self.discharged_from_icu == True:
            self.admitted = False
            
    @api.onchange('admitted', 'discharged_from_icu')
    def onchange_patient(self):
        warning = {}
        result = {}
        if self.name:
            policy_obj = self.search([('name', '=', self.name.id), ('admitted', '=', True)])
            if policy_obj:
                warning = {
                    'title': _('Warning!'),
                    'message':  _('Our records indicate that the patient is already admitted at ICU.')}
            if warning:
                result['warning'] = warning
        return result
            

class MedicalIcuVentilation(models.Model):
    _name = "medical.icu.ventilation"
    _description = 'Mechanical Ventilation History'
    
    def mv_duration(self):
        # Calculate the Mechanical Ventilation time
        now = datetime.now()
        mv_init = now
        mv_finnish = now
        for obj in self:
            if obj.mv_start:
                mv_init = datetime.strptime(str(obj.mv_start), '%Y-%m-%d %H:%M:%S')
            if obj.mv_end:
                mv_finnish = datetime.strptime(str(obj.mv_end), '%Y-%m-%d %H:%M:%S')
                delta = relativedelta(mv_finnish, mv_init)
            else:
                delta = relativedelta(now, mv_init)

            years_months_days = str(delta.years) + 'y ' \
                    + str(delta.months) + 'm ' \
                    + str(delta.days) + 'd '\
                    + str(delta.hours) + 'h ' + str(delta.minutes) + 'mints '
            obj.mv_period = years_months_days
    
    @api.constrains('name')
    def _check_currency_and_amount(self):
        self._cr.execute('select count(name) from medical_inpatient_icu where name = {0} and admitted '.format(self.name.id))
        if self._cr.fetchone()[0] > 1:
            raise ValidationError(_("Our records indicate that the patient is already on Mechanical Ventilation."))
    
    name = fields.Many2one('medical.inpatient.icu', 'Patient ICU Admission', required=True)
    ventilation = fields.Selection([
        ('none', 'None - Maintains Own'),
        ('nppv', 'Non-Invasive Positive Pressure'),
        ('ett', 'ETT'),
        ('tracheostomy', 'Tracheostomy')], 'Type', help="NPPV = Non-Invasive Positive Pressure Ventilation, BiPAP-CPAP \n ETT - Endotracheal Tube",)
    ett_size = fields.Integer('ETT Size')
    tracheostomy_size = fields.Integer('Tracheostomy size')
    mv_start = fields.Datetime('From', help="Start of Mechanical Ventilation", required=True)
    mv_end = fields.Datetime('To', help="End of Mechanical Ventilation")
    mv_period = fields.Char("Duration", size=128, store=True, compute='mv_duration')
    current_mv = fields.Boolean('Current', default=True)
    remarks = fields.Char('Remarks')


class MedicalIcuGlasgow(models.Model):
    _name = "medical.icu.glasgow"
    _description = 'Glasgow Coma Scale'
    
    name = fields.Many2one('medical.inpatient.registration', 'Registration Code', required=True)
    evaluation_date = fields.Datetime('Date', help="Date / Time", required=True, default=fields.Datetime.now)
    glasgow = fields.Integer('Glasgow', default='15', help='Level of Consciousness - on Glasgow Coma Scale :  < 9 severe - 9-12 Moderate, > 13 minor')
    glasgow_eyes = fields.Selection([
        ('1', '1 : Does not Open Eyes'),
        ('2', '2 : Opens eyes in response to painful stimuli'),
        ('3', '3 : Opens eyes in response to voice'),
        ('4', '4 : Opens eyes spontaneously')], 'Eyes', default='4')
    glasgow_verbal = fields.Selection([
        ('1', '1 : Makes no sounds'),
        ('2', '2 : Incomprehensible sounds'),
        ('3', '3 : Utters inappropriate words'),
        ('4', '4 : Confused, disoriented'),
        ('5', '5 : Oriented, converses normally')], 'Verbal', default='5')
    glasgow_motor = fields.Selection([
        ('1', '1 : Makes no movement'),
        ('2', '2 : Extension to painful stimuli - decerebrate response -'),
        ('3', '3 : Abnormal flexion to painful stimuli (decorticate response)'),
        ('4', '4 : Flexion / Withdrawal to painful stimuli'),
        ('5', '5 : localizes painful stimuli'),
        ('6', '6 : Obeys commands')], 'Motor', default='6')
    
    @api.onchange('glasgow_motor', 'glasgow_eyes', 'glasgow_verbal')
    def onchange_glasgow(self):
        self.glasgow = int(self.glasgow_motor) + int(self.glasgow_eyes) + int(self.glasgow_verbal)
        
    @api.depends('glasgow', 'glasgow_eyes', 'glasgow_verbal', 'glasgow_motor')
    def name_get(self):
        result = []
        for obj in self:
            name = str( obj.glasgow ) + ': ' + 'E' + obj.glasgow_eyes + ' V' + obj.glasgow_verbal + ' M' + obj.glasgow_motor
            result.append((obj.id, name))
        return result


class MedicalIcuEcg(models.Model):
    _name = "medical.icu.ecg"
    _description = 'ECG'
    
    name = fields.Many2one('medical.inpatient.registration', 'Registration Code', required=True)
    ecg_date = fields.Datetime('Date', required=True, default=fields.Datetime.now)
    lead = fields.Selection([
        ('i', 'I'),
        ('ii', 'II'),
        ('iii', 'III'),
        ('avf', 'aVF'),
        ('avr', 'aVR'),
        ('avl', 'aVL'),
        ('v1', 'V1'),
        ('v2', 'V2'),
        ('v3', 'V3'),
        ('v4', 'V4'),
        ('v5', 'V5'),
        ('v6', 'V6')], 'Lead')
    axis = fields.Selection([
        ('normal', 'Normal Axis'),
        ('left', 'Left deviation'),
        ('right', 'Right deviation'),
        ('extreme_right', 'Extreme right deviation')], 'Axis', required=True)
    rate = fields.Integer('Rate', required=True)
    rhythm = fields.Selection([
        ('regular', 'Regular'),
        ('irregular', 'Irregular')], 'Rhythm', required=True)
    pacemaker = fields.Selection([
        ('sa', 'Sinus Node'),
        ('av', 'Atrioventricular'),
        ('pk', 'Purkinje')], 'Pacemaker', required=True)
    pr = fields.Integer('PR', help="Duration of PR interval in milliseconds")
    qrs = fields.Integer('QRS', help="Duration of QRS interval in milliseconds")
    qt = fields.Integer('QT', help="Duration of QT interval in milliseconds")
    st_segment = fields.Selection([
        ('normal', 'Normal'),
        ('depressed', 'Depressed'),
        ('elevated', 'Elevated')], 'ST Segment', required=True)
    twave_inversion = fields.Boolean('T wave inversion')
    interpretation = fields.Char('Interpretation', size=256, required=True)
    ecg_strip = fields.Binary('ECG Strip')
    
    @api.depends('interpretation', 'rate')
    def name_get(self):
        result = []
        for obj in self:
            name = obj.rate
            if obj.interpretation:
                name = str(obj.interpretation) + ' // Rate ' + str(name)
            result.append((obj.id, name))
        return result


class MedicalIcuApache(models.Model):
    _name = "medical.icu.apache2"
    _description = 'Apache II scoring'
    
    name = fields.Many2one('medical.inpatient.registration', 'Registration Code', required=True)
    score_date = fields.Datetime('Date', help="Date of the score", required=True)
    age = fields.Integer('Age', help='Patient age in years')
    temperature = fields.Float('Temperature', help='Rectal temperature')
    mean_ap = fields.Integer('MAP', help='Mean Arterial Pressure')
    heart_rate = fields.Integer('Heart Rate')
    respiratory_rate = fields.Integer('Respiratory Rate')
    fio2 = fields.Float('FiO2')
    pao2 = fields.Integer('PaO2')
    paco2 = fields.Integer('PaCO2')
    aado2 = fields.Integer('A-a DO2')
    ph = fields.Float('pH')
    serum_sodium = fields.Integer('Sodium')
    serum_potassium = fields.Float('Potassium')
    serum_creatinine = fields.Float('Creatinine')
    arf = fields.Boolean('ARF', help='Acute Renal Failure')
    wbc = fields.Float('WBC', help="White blood cells x 1000 - if you want to input 4500 wbc / ml, type in 4.5")
    hematocrit = fields.Float('Hematocrit')
    gcs =  fields.Integer('GSC', help='Last Glasgow Coma Scale You can use the GSC calculator from the Patient Evaluation Form.')
    chronic_condition = fields.Boolean('Chronic condition', help='Organ Failure or immunocompromised patient')
    hospital_admission_type = fields.Selection([
        ('me', 'Medical or emergency postoperative'),
        ('el', 'elective postoperative')], 'Hospital Admission Type')
    apache_score = fields.Integer('Score')
    
    @api.onchange('fio2', 'paco2', 'pao2')
    def on_change_with_aado2(self):
        self.aado2 = (713 * self.fio2) - (self.paco2 / 0.8) - self.pao2
        
    @api.onchange('temperature', 'mean_ap', 'heart_rate', 'respiratory_rate', 'fio2', 'pao2', 'aado2', 'ph', 'serum_sodium', 'serum_potassium', 'serum_creatinine', 'arf', 'wbc', 'hematocrit', 'chronic_condition', 'hospital_admission_type')
    def on_change_with_apache_score(self):
        total = 0
        # Age
        if (self.age):
            if (self.age > 44 and self.age < 55):
                self.apache_score = total + 2
            elif (self.age > 54 and self.age < 65):
                self.apache_score = total + 3
            elif (self.age > 64 and self.age < 75):
                self.apache_score = total + 5
            elif (self.age > 74):
                self.apache_score = total + 6
 
        # Temperature
        if (self.temperature):
            if ((self.temperature >= 38.5 and self.temperature < 39) or (self.temperature >= 34 and self.temperature < 36)):
                    self.apache_score = total + 1
            elif (self.temperature >= 32 and self.temperature < 34):
                self.apache_score = total + 2
            elif ((self.temperature >= 30 and self.temperature < 32) or (self.temperature >= 39 and self.temperature < 41)):
                self.apache_score = total + 3
            elif (self.temperature >= 41 or self.temperature < 30):
                self.apache_score = total + 4
 
        # Mean Arterial Pressure (MAP)
        if (self.mean_ap):
            if ((self.mean_ap >= 110 and self.mean_ap < 130) or (self.mean_ap >= 50 and self.mean_ap < 70)):
                    self.apache_score = total + 2
            elif (self.mean_ap >= 130 and self.mean_ap < 160):
                self.apache_score = total + 3
            elif (self.mean_ap >= 160 or self.mean_ap < 50):
                self.apache_score = total + 4
 
        # Heart Rate
        if (self.heart_rate):
            if ((self.heart_rate >= 55 and self.heart_rate < 70) or (self.heart_rate >= 110 and self.heart_rate < 140)):
                    self.apache_score = total + 2
            elif ((self.heart_rate >= 40 and self.heart_rate < 55) or (self.heart_rate >= 140 and self.heart_rate < 180)):
                    self.apache_score = total + 3
            elif (self.heart_rate >= 180 or self.heart_rate < 40):
                self.apache_score = total + 4
 
        # Respiratory Rate
        if (self.respiratory_rate):
            if ((self.respiratory_rate >= 10 and self.respiratory_rate < 12) or (self.respiratory_rate >= 25 and self.respiratory_rate < 35)):
                    self.apache_score = total + 1
            elif (self.respiratory_rate >= 6 and self.respiratory_rate < 10):
                    self.apache_score = total + 2
            elif (self.respiratory_rate >= 35 and self.respiratory_rate < 50):
                    self.apache_score = total + 3
            elif (self.respiratory_rate >= 50 or self.respiratory_rate < 6):
                self.apache_score = total + 4
 
        # FIO2
        if (self.fio2 and (self.aado2 or self.pao2)):
            # If Fi02 is greater than 0.5, we measure the AaDO2 gradient
            # Otherwise, we take into account the Pa02 value
 
            if (self.fio2 >= 0.5):
                if (self.aado2 >= 200 and self.aado2 < 350):
                    self.apache_score = total + 2
 
                elif (self.aado2 >= 350 and self.aado2 < 500):
                    self.apache_score = total + 3
 
                elif (self.aado2 >= 500):
                    self.apache_score = total + 4
 
            else:
                if (self.pao2 >= 61 and self.pao2 < 71):
                    self.apache_score = total + 1
 
                elif (self.pao2 >= 55 and self.pao2 < 61):
                    self.apache_score = total + 3
 
                elif (self.pao2 < 55):
                    self.apache_score = total + 4

        # Arterial pH
        if (self.ph):
            if (self.ph >= 7.5 and self.ph < 7.6):
                self.apache_score = total + 1
            elif (self.ph >= 7.25 and self.ph < 7.33):
                self.apache_score = total + 2
            elif ((self.ph >= 7.15 and self.ph < 7.25) or (self.ph >= 7.6 and self.ph < 7.7)):
                self.apache_score = total + 3
            elif (self.ph >= 7.7 or self.ph < 7.15):
                self.apache_score = total + 4
 
        # Serum Sodium
        if (self.serum_sodium):
            if (self.serum_sodium >= 150 and self.serum_sodium < 155):
                self.apache_score = total + 1
            elif ((self.serum_sodium >= 155 and self.serum_sodium < 160) or (self.serum_sodium >= 120 and self.serum_sodium < 130)):
                self.apache_score = total + 2
            elif ((self.serum_sodium >= 160 and self.serum_sodium < 180) or (self.serum_sodium >= 111 and self.serum_sodium < 120)):
                self.apache_score = total + 3
            elif (self.serum_sodium >= 180 or self.serum_sodium < 111):
                self.apache_score = total + 4
 
        # Serum Potassium
        if (self.serum_potassium):
            if ((self.serum_potassium >= 3 and self.serum_potassium < 3.5) or (self.serum_potassium >= 5.5 and self.serum_potassium < 6)):
                self.apache_score = total + 1
            elif (self.serum_potassium >= 2.5 and self.serum_potassium < 3):
                self.apache_score = total + 2
            elif (self.serum_potassium >= 6 and self.serum_potassium < 7):
                self.apache_score = total + 3
            elif (self.serum_potassium >= 7 or self.serum_potassium < 2.5):
                self.apache_score = total + 4
 
        # Serum Creatinine
        if (self.serum_creatinine):
            arf_factor = 1
            if (self.arf):
            # We multiply by 2 the score if there is concomitant ARF
                arf_factor = 2
            if ((self.serum_creatinine < 0.6) or (self.serum_creatinine >= 1.5 and self.serum_creatinine < 2)):
                    self.apache_score = total + 2*arf_factor
            elif (self.serum_creatinine >= 2 and self.serum_creatinine < 3.5):
                self.apache_score = total + 3*arf_factor
            elif (self.serum_creatinine >= 3.5):
                self.apache_score = total + 4*arf_factor
 
        # Hematocrit
        if (self.hematocrit):
            if (self.hematocrit >= 46 and self.hematocrit < 50):
                self.apache_score = total + 1
            elif ((self.hematocrit >= 50 and self.hematocrit < 60) or (self.hematocrit >= 20 and self.hematocrit < 30)):
                self.apache_score = total + 2
            elif (self.hematocrit >= 60 or self.hematocrit < 20):
                self.apache_score = total + 4
 
        # WBC ( x 1000 )
        if (self.wbc):
            if (self.wbc >= 15 and self.wbc < 20):
                self.apache_score = total + 1
            elif ((self.wbc >= 20 and self.wbc < 40) or (self.wbc >= 1 and self.wbc < 3)):
                self.apache_score = total + 2
            elif (self.wbc >= 40 or self.wbc < 1):
                self.apache_score = total + 4
 
        # Immnunocompromised or severe organ failure
        if (self.chronic_condition and self.hospital_admission_type):
            if (self.hospital_admission_type == 'me'):
                self.apache_score = total + 5
            else:
                self.apache_score = total + 2


class MedicalIcuChestDrainage(models.Model):
    _name = "medical.icu.chest_drainage"
    _description = 'Chest Drainage Asessment'
    
    name = fields.Many2one('medical.patient.rounding', 'Rounding', required=True)
    location = fields.Selection([
        ('rl', 'Right Pleura'),
        ('ll', 'Left Pleura'),
        ('mediastinum', 'Mediastinum')], 'Location')
    fluid_aspect = fields.Selection([
        ('serous', 'Serous'),
        ('bloody', 'Bloody'),
        ('chylous', 'Chylous'),
        ('purulent', 'Purulent')], 'Aspect')
    suction = fields.Boolean('Suction')
    suction_pressure = fields.Integer('cm H2O')
    oscillation = fields.Boolean('Oscillation')
    air_leak = fields.Boolean('Air Leak')
    fluid_volume = fields.Integer('Volume')
    remarks = fields.Char('Remarks', size=256)
    

class MedicalPatientRounding(models.Model):
    # Nursing Rounding for ICU
    # Inherit and append to the existing model the new functionality for ICU
    _inherit = "medical.patient.rounding"
    _description = 'Patient Rounding'
    
    icu_patient = fields.Boolean('ICU', help='Check this box if this is an Intensive Care Unit rounding.')
    gcs = fields.Many2one('medical.icu.glasgow', 'GCS', domain="[('name','=',name)]")
    pupil_dilation = fields.Selection([
        ('normal', 'Normal'),
        ('miosis', 'Miosis'),
        ('mydriasis', 'Mydriasis')], 'Pupil Dilation', default='normal')
    left_pupil = fields.Integer('L', help="size in mm of left pupil")
    right_pupil = fields.Integer('R', help="size in mm of right pupil")
    anisocoria = fields.Boolean('Anisocoria')
    pupillary_reactivity = fields.Selection([
        ('brisk', 'Brisk'),
        ('sluggish', 'Sluggish'),
        ('nonreactive', 'Nonreactive')], 'Pupillary Reactivity')
    pupil_consensual_resp = fields.Boolean('Consensual Response', help="Pupillary Consensual Response")
    # Mechanical ventilation information is on the patient ICU general info
    respiration_type = fields.Selection([
        ('regular', 'Regular'),
        ('deep', 'Deep'),
        ('shallow', 'Shallow'),
        ('labored', 'Labored'),
        ('intercostal', 'Intercostal')], 'Respiration')
    oxygen_mask = fields.Boolean('Oxygen Mask')
    fio2 = fields.Integer('FiO2')
    peep = fields.Boolean('PEEP')
    peep_pressure = fields.Integer('cm H2O', help="Pressure")
    sce = fields.Boolean('SCE', help="Subcutaneous Emphysema")
    lips_lesion = fields.Boolean('Lips lesion')
    oral_mucosa_lesion = fields.Boolean('Oral mucosa lesion')
    # Chest expansion characteristics
    chest_expansion = fields.Selection([
        ('symmetric', 'Symmetrical'),
        ('asymmetric', 'Asymmetrical')], 'Expansion')
    paradoxical_expansion = fields.Boolean('Paradoxical', help="Paradoxical Chest Expansion")
    tracheal_tug = fields.Boolean('Tracheal Tug')
    # Trachea position
    trachea_alignment = fields.Selection([
        ('midline', 'Midline'),
        ('right', 'Deviated right'),
        ('left', 'Deviated left')], 'Tracheal alignment')
    # Chest Drainages
    chest_drainages = fields.One2many('medical.icu.chest_drainage', 'name', "Drainages")
    # Chest X-Ray
    xray = fields.Binary('Xray')
    # Cardiovascular assessment
    ecg = fields.Many2one('medical.icu.ecg', 'ECG', domain="[('name','=',name)]")
    venous_access = fields.Selection([
        ('none', 'None'),
        ('central', 'Central catheter'),
        ('peripheral', 'Peripheral')], 'Venous Access')
    swan_ganz = fields.Boolean('Swan Ganz', help="Pulmonary Artery Catheterization - PAC -")
    arterial_access = fields.Boolean('Arterial Access')
    dialysis = fields.Boolean('Dialysis')
    edema = fields.Selection([
        ('none', 'None'),
        ('peripheral', 'Peripheral'),
        ('anasarca', 'Anasarca')], 'Edema')
    # Blood & Skin
    bacteremia = fields.Boolean('Bacteremia')
    ssi = fields.Boolean('Surgery Site Infection')
    wound_dehiscence = fields.Boolean('Wound Dehiscence')
    cellulitis = fields.Boolean('Cellulitis')
    necrotizing_fasciitis = fields.Boolean('Necrotizing fasciitis')
    # Abdomen & Digestive
    vomiting = fields.Selection([
        ('none', 'None'),
        ('vomiting', 'Vomiting'),
        ('hematemesis', 'Hematemesis')], 'Vomiting')
    bowel_sounds = fields.Selection([
        ('normal', 'Normal'),
        ('increased', 'Increased'),
        ('decreased', 'Decreased'),
        ('absent', 'Absent')], 'Bowel Sounds')
    stools = fields.Selection([
        ('normal', 'Normal'),
        ('constipation', 'Constipation'),
        ('diarrhea', 'Diarrhea'),
        ('melena', 'Melena')], 'Stools')
    peritonitis = fields.Boolean('Peritonitis signs')

    @api.onchange('left_pupil', 'right_pupil')
    def on_change_with_aado2(self):
        if (self.left_pupil == self.right_pupil):
            self.anisocoria = False
        else:
            self.anisocoria = True
