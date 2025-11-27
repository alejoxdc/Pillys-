# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _
from datetime import datetime
from dateutil.relativedelta import relativedelta


class MedicalPerinatalMonitor (models.Model):
	_name = "medical.perinatal.monitor"
	_description = "Perinatal monitor"
	
	name = fields.Many2one('medical.perinatal', 'Patient Perinatal Evaluation')
	date = fields.Datetime('Date and Time')
	systolic = fields.Integer('Systolic Pressure')
	diastolic = fields.Integer('Diastolic Pressure')
	contractions = fields. Integer('Contractions')
	frequency = fields.Integer('Mother\'s Heart Frequency')
	dilation = fields. Integer('Cervix dilation')
	f_frequency = fields.Integer('Fetus Heart Frequency')
	meconium = fields.Boolean('Meconium')
	bleeding = fields.Boolean('Bleeding')
	fundal_height = fields.Integer('Fundal Height')
	fetus_position = fields.Selection([
		('n', 'Correct'),
		('o', 'Occiput / Cephalic Posterior'),
		('fb', 'Frank Breech'),
		('cb', 'Complete Breech'),
		('t', 'Transverse Lie'),
		('t', 'Footling Breech')], 'Fetus Position', index=True)


# class newborn (models.Model):
# 	_name = "medical.newborn"
# 	_description = "newborn information"
# 	_columns = {
# 		'name = fields.Char ('Baby\'s name',size=128),
# 		'code = fields.Char ('Newborn ID', size=64,required=True),
#                 'birth_date = fields.Datetime('Date of Birth', required=True),
# 		'photo = fields.binary ('Picture'),
# 		'sex = fields.Selection([
#                                 ('m','Male'),
#                                 ('f','Female'),
#                                 ], 'Sex', index=True, required=True),
# 		'cephalic_perimeter = fields.Integer ('Cephalic Perimeter'),
# 		'length = fields.Integer ('Length'),
# 		'weight = fields.Integer ('Weight'),
#         'apgar1 = fields.Integer('APGAR 1st minute'),
#         'apgar5 = fields.Integer('APGAR 5th minute'),
# 		'meconium': fields.Boolean ('Meconium'),
# 		'congenital_diseases = fields.many2many ('medical.patient.disease', 'newborn_disease_rel','patient_id','congenital_id', 'Congenital diseases'),
# 		'reanimation_stimulation =fields.Boolean ('Stimulation'),
# 		'reanimation_aspiration =fields.Boolean ('Aspiration'),
# 		'reanimation_intubation =fields.Boolean ('Intubation'),
# 		'reanimation_mask =fields.Boolean ('Mask'),
# 		'reanimation_oxygen =fields.Boolean ('Oxygen'),
# 		'test_vdrl = fields.Boolean ('VDRL'),
# 		'test_toxo = fields.Boolean ('Toxoplasmosis'),
# 		'test_chagas = fields.Boolean ('Chagas'),
# 		'test_billirubin = fields.Boolean ('Billirubin'),
# 		'test_audition = fields.Boolean ('Audition'),
# 		'test_metabolic = fields.Boolean ('The metabolic / genetic ("heel stick")', help="Test for Fenilketonuria, Congenital Hypothyroidism, Quistic Fibrosis, Galactosemia"),
# 		'medication = fields.many2many('medical.medicament', 'newborn_labor_rel','medicament_id','patient_id','Medicaments and anesthesics'),
# 		'responsible = fields.Many2one('medical.physician','Doctor in Charge', help="Signed by the health professional"), 
# 		'dismissed = fields.Datetime('Dismissed from hospital'),
# 		'bd = fields.Boolean ('Born dead'),
# 		'died_at_delivery = fields.Boolean ('Died at delivery room'),
# 		'died_at_the_hospital = fields.Boolean ('Died at the hospital'),
# 		'died_being_transferred = fields.Boolean ('Died being transferred',help="The baby died being transferred to another health institution"),
# 		'tod = fields.Datetime('Time of Death'),
# 		'cod = fields.Many2one('medical.pathology', 'Cause of death'),
# 		'notes = fields.text ('Notes'),
# 		
# 	}
# 	_sql_constraints = [
#                 ('code_uniq', 'unique (code)', 'The newborn ID must be unique')]
# 
# newborn ()

class MedicalPuerperiumMonitor (models.Model):
	_name = "medical.puerperium.monitor"
	_description = "Puerperium Monitor"
	
	name_id = fields.Many2one('medical.patient.pregnancy', 'Patient Pregnancy ID')
	name = fields.Char('Internal code', size=64)
	date = fields.Datetime('Date and Time', required=True)
	systolic = fields.Integer('Systolic Pressure')
	diastolic = fields.Integer('Diastolic Pressure')
	frequency = fields.Integer('Heart Frequency')
	lochia_amount = fields.Selection([
		('n', 'normal'),
		('e', 'abundant'),
		('h', 'hemorrhage')], 'Lochia amount', index=True)
	lochia_color = fields.Selection([
		('r', 'rubra'),
		('s', 'serosa'),
		('a', 'alba')], 'Lochia color', index=True)
	lochia_odor = fields.Selection([
		('n', 'normal'),
		('o', 'offensive')], 'Lochia odor', index=True)
	uterus_involution = fields.Integer('Fundal Height', help="Distance between the symphysis pubis and the uterine fundus (S-FD) in cm")
	temperature = fields.Float('Temperature')


class MedicalPerinatal (models.Model):
	_name = "medical.perinatal"
	_description = "perinatal information"
	
	def get_perinatal_information(self):
		if self.admission_date and self.name:
			self.gestational_days = datetime.datetime(self.admission_date) - self.name.lmp
			self.gestational_weeks = self.gestational_days / 7	

	name = fields.Many2one('medical.patient.pregnancy', 'Patient Pregnancy')
	admission_code = fields.Char('Code')
	gravida_number = fields.Integer('Gravida')
	abortion = fields.Boolean('Abortion')
	admission_date = fields.Datetime('Admission date', help="Date when she was admitted to give birth")
	prenatal_evaluations = fields.Integer('Prenatal evaluations', help="Number of visits to the doctor during pregnancy")
	start_labor_mode = fields.Selection([
		('n', 'Normal'),
		('i', 'Induced'),
		('c', 'c-section')], 'Labor mode', index=True)
	gestational_weeks = fields.Integer('Gestational Weeks', compute='get_perinatal_information', store=True)
	gestational_days = fields.Integer('Gestational days', compute='get_perinatal_information', store=True)
	fetus_presentation = fields.Selection([
		('n', 'Correct'),
		('o', 'Occiput / Cephalic Posterior'),
		('fb', 'Frank Breech'),
		('cb', 'Complete Breech'),
		('t', 'Transverse Lie'),
		('t', 'Footling Breech')], 'Fetus Presentation', index=True)
	dystocia = fields.Boolean('Dystocia')
	placenta_incomplete = fields.Boolean('Incomplete Placenta')
	placenta_retained = fields.Boolean('Retained Placenta')
	abruptio_placentae = fields.Boolean('Abruptio Placentae', help='Abruptio Placentae')
	episiotomy = fields.Boolean('Episiotomy')
	vaginal_tearing = fields.Boolean('Vaginal tearing')
	forceps = fields.Boolean('Use of forceps')
	monitoring = fields.One2many('medical.perinatal.monitor', 'name', 'Monitors')
	laceration = fields.Selection([
		('perineal', 'Perineal'),
		('vaginal', 'Vaginal'),
		('cervical', 'Cervical'),
		('broad_ligament', 'Broad Ligament'),
		('vulvar', 'Vulvar'),
		('rectal', 'Rectal'),
		('bladder', 'Bladder'),
		('urethral', 'Urethral')], 'Lacerations', index=True)
	hematoma = fields.Selection([
		('vaginal', 'Vaginal'),
		('vulvar', 'Vulvar'),
		('retroperitoneal', 'Retroperitoneal')], 'Hematoma', index=True)
	medication = fields.One2many('medical.patient.medication', 'name', 'Medication and anesthesics')
	dismissed = fields.Datetime('Dismissed from hospital')
	place_of_death = fields.Selection([
		('ho', 'Hospital'),
		('dr', 'At the delivery room'),
		('hh', 'in transit to the hospital'),
		('th', 'Being transferred to other hospital')], 'Place of Death', help="Place where the mother died", index=True)
	mother_deceased = fields.Boolean('Maternal death', help="Mother died in the process")
	notes = fields.Text('Notes')

	_sql_constraints = [('gravida_number_uniq', 'unique (gravida_number)', 'The Gravida Number must be unique.')]


# Add to the Medical patient_data class (medical.patient) the gynecological and obstetric fields.

class MedicalPatient (models.Model):
	_name = "medical.patient"
	_inherit = "medical.patient"
	
	
# 	def get_pregnancy_info(self, cr, uid, ids, field_name, arg, context=None):		
# 		data_obj = self.browse(cr, uid, ids)[0]
# 		if field_name == 'currently_pregnant':
# 			for pregnancy_history in data_obj.pregnancy_history:
# 				if pregnancy_history.current_pregnancy:
# 					return True
# 		return False
			
	# 'currently_pregnant = fields.function(get_pregnancy_info, method=True, string='Pregnant', type='Boolean'),
	fertile = fields.Boolean('Fertile', help="Check if patient is in fertile age")
	menarche = fields.Integer('Menarche age')
	menopausal = fields.Boolean('Menopausal')
	menopause = fields.Integer('Menopause age')
	mammography = fields.Boolean('Mammography', help="Check if the patient does periodic mammographys")
	# 'mammography_last = fields.Date ('Last mammography',help="Enter the date of the last mammography"),
	breast_self_examination = fields.Boolean('Breast self-examination', help="Check if the patient does and knows how to self examine her breasts")
	pap_test = fields.Boolean('PAP test', help="Check if the patient does periodic cytologic pelvic smear screening")
	pap_test_last = fields.Date('Last PAP test', help="Enter the date of the last Papanicolau test")
	colposcopy = fields.Boolean('Colposcopy', help="Check if the patient has done a colposcopy exam")
	# 'colposcopy_last = fields.Date ('Last colposcopy',help="Enter the date of the last colposcopy"),

	gravida = fields.Integer('Pregnancies', help="Number of pregnancies")
	premature = fields.Integer('Premature', help="Premature Deliveries")
	abortions = fields.Integer('Abortions')
	stillbirths = fields.Integer('Stillbirths')
	full_term = fields.Integer('Full Term', help="Full term pregnancies")
	gpa = fields.Char('GPA', size=32, help="Gravida, Para, Abortus Notation. For example G4P3A1 : 4 Pregnancies, 3 viable and 1 abortion")
	born_alive = fields.Integer('Born Alive')
	deaths_1st_week = fields.Integer('Deceased during 1st week', help="Number of babies that die in the first week")
	deaths_2nd_week = fields.Integer('Deceased after 2nd week', help="Number of babies that die after the second week")
	perinatal = fields.Many2many('medical.perinatal', 'patient_perinatal_rel', 'patient_id', 'perinatal_id', 'Perinatal Info')
	
	menstrual_history = fields.One2many('medical.patient.menstrual_history', 'name', 'Menstrual History')
	mammography_history = fields.One2many('medical.patient.mammography_history', 'name', 'Mammography History')
	pap_history = fields.One2many('medical.patient.pap_history', 'name', 'PAP smear History')
	colposcopy_history = fields.One2many('medical.patient.colposcopy_history', 'name', 'Colposcopy History')
	pregnancy_history = fields.One2many('medical.patient.pregnancy', 'name', 'Pregnancies')


class PatientMenstrualHistory(models.Model):
	_name = 'medical.patient.menstrual_history'
	
	name = fields.Many2one('medical.patient', 'Patient', required=True, readonly=True)
	evaluation = fields.Many2one('medical.patient.evaluation', 'Evaluation')
	evaluation_date = fields.Date('Date', default=fields.Datetime.now)
	lmp = fields.Date('LMP', help="Last Menstrual Period", required=True)
	lmp_length = fields.Integer('Length', required=True)
	is_regular = fields.Boolean('Regular')
	dysmenorrhea = fields.Boolean('Dysmenorrhea')
	frequency = fields.Selection([
		('amenorrhea', 'amenorrhea'),
		('oligomenorrhea', 'oligomenorrhea'),
		('eumenorrhea', 'eumenorrhea'),
		('polymenorrhea', 'polymenorrhea')], 'Frequency', default='eumenorrhea', index=True)
	volume = fields.Selection([
		('hypomenorrhea', 'hypomenorrhea'),
		('normal', 'normal'),
		('menorrhagia', 'menorrhagia')], 'Volume', default='normal',  index=True)
	

class PatientMammographyHistory(models.Model):
	_name = 'medical.patient.mammography_history'
	
	name = fields.Many2one('medical.patient', 'Patient', required=True, readonly=True)
	evaluation = fields.Many2one('medical.patient.evaluation', 'Evaluation')
	evaluation_date = fields.Date('Date', default=fields.Datetime.now)
	last_mammography = fields.Date('Date', help="Last Mammography", default=fields.Datetime.now)
	result = fields.Selection([
		('normal', 'normal'),
		('abnormal', 'abnormal')], 'Result', help="Please check the lab results if the module is installed")
	comments = fields.Char('Remarks')
		

class PatientPAPHistory(models.Model):
	_name = 'medical.patient.pap_history'

	name = fields.Many2one('medical.patient', 'Patient', required=True, readonly=True)
	evaluation = fields.Many2one('medical.patient.evaluation', 'Evaluation')
	evaluation_date = fields.Date('Date', default=fields.Datetime.now)
	result = fields.Selection([
		('negative', 'Negative'),
		('c1', 'ASC-US'),
		('c2', 'ASC-H'),
		('g1', 'ASG'),
		('c3', 'LSIL'),
		('c4', 'HSIL'),
		('g4', 'AIS')], 'Result', help="Please check the lab results if the module is installed", index=True)
	comments = fields.Char('Remarks')		


class PatientColposcopyHistory(models.Model):
	_name = 'medical.patient.colposcopy_history'
		
	name = fields.Many2one('medical.patient', 'Patient', required=True, readonly=True)
	evaluation = fields.Many2one('medical.patient.evaluation', 'Evaluation')
	evaluation_date = fields.Date('Date', default=fields.Datetime.now)
	last_colposcopy = fields.Date('Date', help="Last Colposcopy",default=fields.Datetime.now)
	result = fields.Selection([
		('normal', 'normal'),
		('abnormal', 'abnormal')], 'Result', help="Please check the lab results if the module is installed", index=True)
	comments = fields.Char('Remarks')


class PatientPregnancy(models.Model):
	_name = 'medical.patient.pregnancy'
	
	def get_perinatal_information(self):
		d = ''
		if self.lmp:
			self.pdd = datetime.strptime(self.lmp, '%Y-%m-%d') + relativedelta(days=280)
		if self.pregnancy_end_date:
			self.pdd = datetime.date(self.pregnancy_end_date) - self.lmp

	name = fields.Many2one('medical.patient', 'Patient ID')
	gravida = fields.Integer('Pregnancy')
	warning = fields.Boolean('Warn', help='Check this box if this is pregancy is or was NOT normal')
	lmp = fields.Date('LMP', help="Last Menstrual Period", required=True)
	pdd = fields.Char('Pregnancy Due Date', size=64, compute='_get_pregnancy_data_new', store=True, help='Weeks at the end of pregnancy')
	prenatal_evaluations = fields.One2many('medical.patient.prenatal.evaluation', 'name', 'Prenatal Evaluations')
	perinatal = fields.One2many('medical.perinatal', 'name', 'Perinatal Info')
	puerperium_monitor = fields.One2many('medical.puerperium.monitor', 'name_id', 'Puerperium monitor')
	current_pregnancy = fields.Boolean('Current Pregnancy', default=True, help='This field marks the current pregnancy')
	fetuses = fields.Integer('Fetuses', required=True)
	monozygotic = fields.Boolean('Monozygotic')
	pregnancy_end_result = fields.Selection([
		('live_birth', 'Live birth'),
		('abortion', 'Abortion'),
		('stillbirth', 'Stillbirth'),
		('status_unknown', 'Status unknown')], 'Result',)
	pregnancy_end_date = fields.Datetime('End of Pregnancy')
	# 'pregnancy_end_age = fields.function(get_pregnancy_data, string='Weeks', type='Char', help='Weeks at the end of pregnancy'),
	iugr = fields.Selection([
		('symmetric', 'Symmetric'),
		('assymetric', 'Assymetric')], 'IUGR')
	
# 	def check_patient_current_pregnancy(self,cr,uid,ids):
# 		'''Check for only one current pregnancy in the patient'''
# 		data_obj = self.browse(cr, uid, ids)[0]
# 		name = data_obj.name.id
# 		data_ids = self.search(cr, uid, [('name','=',name),('current_pregnancy','=',True)])
# 		if len(data_ids) > 1:
# 			return False 
# 		return True
# 	
# 	_constraints = [
#         (check_patient_current_pregnancy, 'Our records indicate that the patient is already pregnant !', ['name'])]
	
	_sql_constraints = [('gravida_uniq', 'unique (name,gravida)', 'The pregancy number must be unique for this patient !')]


class PrenatalEvaluation(models.Model):
	_name = 'medical.patient.prenatal.evaluation'
		
	def get_patient_evaluation_data(self):
		if self.evaluation_date and self.name:
			self.gestational_weeks = (datetime.datetime.date(self.evaluation_date) - self.name.lmp) / 7
			self.gestational_days = datetime.datetime.date(self.evaluation_date) - self.name.lmp
		
	name = fields.Many2one('medical.patient', 'Patient ID')
	evaluation = fields.Many2one('medical.patient.evaluation', 'Patient Evaluation', readonly=True)
	evaluation_date = fields.Datetime('Date', required=True)
	gestational_weeks = fields.Integer('Gestational Weeks', compute='get_patient_evaluation_data', store=True)
	gestational_days = fields.Integer('Gestational Days', compute='get_patient_evaluation_data', store=True)
	hypertension = fields.Boolean('Hypertension', help='Check this box if the mother has hypertension')
	preeclampsia = fields.Boolean('Preeclampsia', help='Check this box if the mother has pre-eclampsia')
	overweight = fields.Boolean('Overweight', help='Check this box if the mother is overweight or obesity')
	diabetes = fields.Boolean('Diabetes', help='Check this box if the mother has glucose intolerance or diabetes')
	invasive_placentation = fields.Selection([
		('normal', 'Normal decidua'),
		('accreta', 'Accreta'),
		('increta', 'Increta'),
		('percreta', 'Percreta')], 'Placentation')
	placenta_previa = fields.Boolean('Placenta Previa')
	vasa_previa = fields.Boolean('Vasa Previa')
	fundal_height = fields.Integer('Fundal Height', help="Distance between the symphysis pubis and the uterine fundus (S-FD) in cm")
	fetus_heart_rate = fields.Integer('Fetus heart rate', help='Fetus heart rate')
	efw = fields.Integer('EFW', help="Estimated Fetal Weight")
	fetal_bpd = fields.Integer('BPD', help="Fetal Biparietal Diameter")
	fetal_ac = fields.Integer('AC', help="Fetal Abdominal Circumference")
	fetal_hc = fields.Integer('HC', help="Fetal Head Circumference")
	fetal_fl = fields.Integer('FL', help="Fetal Femur Length")
	oligohydramnios = fields.Boolean('Oligohydramnios')
	polihydramnios = fields.Boolean('Polihydramnios')
	iugr = fields.Boolean('IUGR', help="Intra Uterine Growth Restriction")
