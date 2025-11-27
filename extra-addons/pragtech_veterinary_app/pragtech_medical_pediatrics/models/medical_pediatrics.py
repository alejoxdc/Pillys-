import time
from odoo import api, fields, models, tools, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class medical_newborn(models.Model):
    _name = "medical.newborn"
    _description = 'Newborn Information'

    name = fields.Char('Newborn ID', size=256)
    mother = fields.Many2one('medical.patient', 'Mother')
    newborn_name = fields.Char('Baby\'s name', size=256)
    birth_date = fields.Date('Date of Birth', required=True)
    photo = fields.Binary('Picture')
    sex = fields.Selection([('m', 'Male'), ('f', 'Female'), ], 'Sex', required=True)

    cephalic_perimeter = fields.Integer('Cephalic Perimeter', help="Perimeter in centimeters (cm)")
    length = fields.Integer('Length', help="Perimeter in centimeters (cm)")
    weight = fields.Integer('Weight', help="Weight in grams (g)")
    apgar1 = fields.Integer('APGAR 1st minute')
    apgar5 = fields.Integer('APGAR 5th minute')
    apgar_scores = fields.One2many('medical.neonatal.apgar', 'name', 'APGAR scores')
    meconium = fields.Boolean('Meconium')
    congenital_diseases = fields.One2many('medical.patient.disease', 'newborn_id', 'Congenital diseases')
    reanimation_stimulation = fields.Boolean('Stimulation')
    reanimation_aspiration = fields.Boolean('Aspiration')
    reanimation_intubation = fields.Boolean('Intubation')
    reanimation_mask = fields.Boolean('Mask')
    reanimation_oxygen = fields.Boolean('Oxygen')
    test_vdrl = fields.Boolean('VDRL')
    test_toxo = fields.Boolean('Toxoplasmosis')
    test_chagas = fields.Boolean('Chagas')
    test_billirubin = fields.Boolean('Billirubin')
    test_audition = fields.Boolean('Audition')
    test_metabolic = fields.Boolean('Metabolic ("heel stick screening")',
                                    help="Test for Fenilketonuria, Congenital Hypothyroidism, Quistic Fibrosis, Galactosemia")
    neonatal_ortolani = fields.Boolean('Positive Ortolani')
    neonatal_barlow = fields.Boolean('Positive Barlow')
    neonatal_hernia = fields.Boolean('Hernia')
    neonatal_ambiguous_genitalia = fields.Boolean('Ambiguous Genitalia')
    neonatal_erbs_palsy = fields.Boolean('Erbs Palsy')
    neonatal_hematoma = fields.Boolean('Hematomas')
    neonatal_talipes_equinovarus = fields.Boolean('Talipes Equinovarus')
    neonatal_polydactyly = fields.Boolean('Polydactyly')
    neonatal_syndactyly = fields.Boolean('Syndactyly')
    neonatal_moro_reflex = fields.Boolean('Moro Reflex')
    neonatal_grasp_reflex = fields.Boolean('Grasp Reflex')
    neonatal_stepping_reflex = fields.Boolean('Stepping Reflex')
    neonatal_babinski_reflex = fields.Boolean('Babinski Reflex')
    neonatal_blink_reflex = fields.Boolean('Blink Reflex')
    neonatal_sucking_reflex = fields.Boolean('Sucking Reflex')
    neonatal_swimming_reflex = fields.Boolean('Swimming Reflex')
    neonatal_tonic_neck_reflex = fields.Boolean('Tonic Neck Reflex')
    neonatal_rooting_reflex = fields.Boolean('Rooting Reflex')
    neonatal_palmar_crease = fields.Boolean('Transversal Palmar Crease')
    medication_ids = fields.One2many('medical.patient.medication', 'newborn_id', 'Medication')
    responsible = fields.Many2one('medical.physician', 'Doctor in charge', help="Signed by the health professional")
    dismissed = fields.Datetime('Discharged')
    bd = fields.Boolean('Stillbirth')
    died_at_delivery = fields.Boolean('Died at delivery room')
    died_at_the_hospital = fields.Boolean('Died at the hospital')
    died_being_transferred = fields.Boolean('Died being transferred',
                                            help="The baby died being transferred to another health institution")
    tod = fields.Datetime('Time of Death')
    cod = fields.Many2one('medical.pathology', 'Cause of death')
    notes = fields.Text('Notes')

    sql_constraints = [
        ('name_uniq', 'unique (name)', 'The Newborn ID must be unique !')]

    @api.onchange('birth_date')
    def onchange_dob(self):
        c_date = datetime.today().strftime('%Y-%m-%d')
        if self.birth_date:
            #             if not (self.birth_date<=c_date):
            #                 raise UserError(_('Birthdate cannot be After Current Date.'))
            return {}

    @api.model
    def create(self, vals):
        c_date = datetime.today().strftime('%Y-%m-%d')
        if (vals['birth_date'] <= c_date):
            res = super(medical_newborn, self).create(vals)
        else:
            raise UserError(_('Birthdate cannot be After Current Date'))
        return res


class medical_neonatal_apgar(models.TransientModel):
    _name = "medical.neonatal.apgar"
    _description = 'Neonatal APGAR Score'

    name = fields.Many2one('medical.newborn', 'Newborn ID')
    apgar_minute = fields.Integer('Minute', required=True)
    apgar_appearance = fields.Selection([('0', 'central cyanosis'), ('1', 'acrocyanosis'), ('2', 'no cyanosis'), ],
                                        'Appearance', required=True)
    apgar_pulse = fields.Selection([('0', 'Absent'), ('1', '< 100'), ('2', '> 100'), ], 'Pulse', required=True)
    apgar_grimace = fields.Selection([('0', 'No response to stimulation'), ('1', 'grimace when stimulated'),
                                      ('2', 'cry or pull away when stimulated'), ],
                                     'Grimace', required=True)
    apgar_activity = fields.Selection([('1', 'Some flexion'), ('2', 'flexed arms and legs'), ],
                                      'Activity', required=True)
    apgar_respiration = fields.Selection([('0', 'Absent'), ('1', 'Weak / Irregular'), ('2', 'strong'), ],
                                         'Respiration', required=True)
    apgar_score = fields.Integer('APGAR Score')

    @api.onchange('apgar_respiration', 'apgar_activity', 'apgar_grimace', 'apgar_pulse', 'apgar_appearance')
    def on_change_with_apgar_score(self):
        apgar_appearance = self.apgar_appearance or '0'
        apgar_pulse = self.apgar_pulse or '0'
        apgar_grimace = self.apgar_grimace or '0'
        apgar_activity = self.apgar_activity or '0'
        apgar_respiration = self.apgar_respiration or '0'
        v = {}
        apgar_score = int(apgar_appearance) + int(apgar_pulse) + \
                      int(apgar_grimace) + int(apgar_activity) + int(apgar_respiration)
        self.apgar_score = apgar_score


#         v['apgar_score'] = apgar_score
#             
#         return {'value': v}
# 
#         return apgar_score


class medical_patient_medication(models.Model):
    _name = "medical.patient.medication"
    _inherit = "medical.patient.medication"
    _description = 'Neonatal Medication. Inherit and Add field to Medication model'

    newborn_id = fields.Many2one('medical.newborn', 'Newborn ID')


class medical_patient_disease(models.Model):
    _name = "medical.patient.disease"
    _inherit = "medical.patient.disease"
    _description = 'Congenital Diseases. Inherit Disease object for use in neonatology'

    newborn_id = fields.Many2one('medical.newborn', 'Newborn ID')


class medical_patient(models.Model):
    _name = "medical.patient"
    _inherit = "medical.patient"
    _description = 'Medical Patient'

    psc = fields.One2many('medical.patient.psc', 'patient', 'Pediatric Symptoms Checklist')


class appointment(models.Model):
    _name = "medical.appointment"
    _inherit = "medical.appointment"

    ped_id1 = fields.Many2many('medical.patient.psc', 'ped_apt_rel', 'evaluation_date', 'apt1', 'Pediatric Symptoms')


class medical_patient_psc(models.Model):
    _name = "medical.patient.psc"
    _description = 'Pediatric Symptoms Checklist'
    _rec_name = 'patient'

    patient = fields.Many2one('medical.newborn', 'Patient', required=True)
    evaluation_date = fields.Many2one('medical.appointment', 'Appointment',
                                      help="Enter or select the date / ID of the appointment related to this evaluation")
    evaluation_start = fields.Datetime('Date', required=True)
    user_id = fields.Many2one('res.users', 'Healh Professional', readonly=True, default=lambda self: self.env.user)
    notes = fields.Text('Notes')
    psc_aches_pains = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Complains of aches and pains')

    psc_spend_time_alone = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Spends more time alone')

    psc_tires_easily = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Tires easily, has little energy')

    psc_fidgety = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Fidgety, unable to sit still')

    psc_trouble_with_teacher = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Has trouble with teacher')

    psc_less_interest_in_school = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Less interested in school')

    psc_acts_as_driven_by_motor = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Acts as if driven by a motor')

    psc_daydreams_too_much = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Daydreams too much')

    psc_distracted_easily = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Distracted easily')

    psc_afraid_of_new_situations = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Is afraid of new situations')

    psc_sad_unhappy = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Feels sad, unhappy')

    psc_irritable_angry = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Is irritable, angry')

    psc_feels_hopeless = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Feels hopeless')

    psc_trouble_concentrating = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Has trouble concentrating')

    psc_less_interested_in_friends = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Less interested in friends')

    psc_fights_with_others = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Fights with other children')

    psc_absent_from_school = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Absent from school')

    psc_school_grades_dropping = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'School grades dropping')

    psc_down_on_self = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Is down on him or herself')

    psc_visit_doctor_finds_ok = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Visits the doctor with doctor finding nothing wrong')

    psc_trouble_sleeping = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Has trouble sleeping')

    psc_worries_a_lot = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Worries a lot')

    psc_wants_to_be_with_parents = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Wants to be with you more than before')

    psc_feels_is_bad_child = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Feels he or she is bad')

    psc_takes_unnecesary_risks = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Takes unnecessary risks')

    psc_gets_hurt_often = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Gets hurt frequently')

    psc_having_less_fun = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Seems to be having less fun')

    psc_act_as_younger = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Acts younger than children his or her age')

    psc_does_not_listen_to_rules = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Does not listen to rules')

    psc_does_not_show_feelings = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Does not show feelings')

    psc_does_not_get_people_feelings = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Does not get people feelings')

    psc_teases_others = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Teases others')

    psc_blames_others = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Blames others for his or her troubles')

    psc_takes_things_from_others = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Takes things that do not belong to him or her')

    psc_refuses_to_share = fields.Selection([
        ('0', 'Never'),
        ('1', 'Sometimes'),
        ('2', 'Often'),
    ], 'Refuses to share')

    psc_total = fields.Integer('PSC Total', default=0)
    ped_id = fields.Many2one('medical.appointment', 'pediatric')

    _sql_constraints = [
        ('evaluation_date', 'unique (evaluation_date)', 'The Appointment must be unique')]

    @api.model
    def create(self, vals):
        id = super(medical_patient_psc, self).create(vals)
        if vals['evaluation_date']:
            self._cr.execute('insert into ped_apt_rel(evaluation_date,apt1) values (%s,%s)',
                             (vals['evaluation_date'], id.id))
        return id

    def write(self, vals, ):
        if 'evaluation_date' in vals and vals['evaluation_date']:
            self._cr.execute('insert into ped_apt_rel(evaluation_date,apt1) values (%s,%s)',
                             (vals['evaluation_date'], self._ids[0]))
        return super(medical_patient_psc, self).write(vals)

    @api.onchange(
        'psc_aches_pains', 'psc_spend_time_alone', 'psc_tires_easily', 'psc_fidgety',
        'psc_trouble_with_teacher', 'psc_less_interest_in_school', 'psc_acts_as_driven_by_motor',
        'psc_daydreams_too_much', 'psc_distracted_easily',
        'psc_afraid_of_new_situations', 'psc_sad_unhappy', 'psc_irritable_angry', 'psc_feels_hopeless',
        'psc_trouble_concentrating',
        'psc_less_interested_in_friends', 'psc_fights_with_others', 'psc_absent_from_school',
        'psc_school_grades_dropping',
        'psc_down_on_self', 'psc_visit_doctor_finds_ok', 'psc_trouble_sleeping', 'psc_worries_a_lot',
        'psc_wants_to_be_with_parents',
        'psc_feels_is_bad_child', 'psc_takes_unnecesary_risks', 'psc_gets_hurt_often', 'psc_having_less_fun',
        'psc_act_as_younger',
        'psc_does_not_listen_to_rules', 'psc_does_not_show_feelings', 'psc_does_not_get_people_feelings',
        'psc_teases_others',
        'psc_takes_things_from_others', 'psc_refuses_to_share'

    )
    def on_change_with_psc_total(self):

        psc_aches_pains = self.psc_aches_pains or '0'
        psc_spend_time_alone = self.psc_spend_time_alone or '0'
        psc_tires_easily = self.psc_tires_easily or '0'
        psc_fidgety = self.psc_fidgety or '0'
        psc_trouble_with_teacher = self.psc_trouble_with_teacher or '0'
        psc_less_interest_in_school = self.psc_less_interest_in_school or '0'
        psc_acts_as_driven_by_motor = self.psc_acts_as_driven_by_motor or '0'
        psc_daydreams_too_much = self.psc_daydreams_too_much or '0'
        psc_distracted_easily = self.psc_distracted_easily or '0'
        psc_afraid_of_new_situations = self.psc_afraid_of_new_situations or '0'
        psc_sad_unhappy = self.psc_sad_unhappy or '0'
        psc_irritable_angry = self.psc_irritable_angry or '0'
        psc_feels_hopeless = self.psc_feels_hopeless or '0'
        psc_trouble_concentrating = self.psc_trouble_concentrating or '0'
        psc_less_interested_in_friends = self.psc_less_interested_in_friends or '0'
        psc_fights_with_others = self.psc_fights_with_others or '0'
        psc_absent_from_school = self.psc_absent_from_school or '0'
        psc_school_grades_dropping = self.psc_school_grades_dropping or '0'
        psc_down_on_self = self.psc_down_on_self or '0'
        psc_visit_doctor_finds_ok = self.psc_visit_doctor_finds_ok or '0'
        psc_trouble_sleeping = self.psc_trouble_sleeping or '0'
        psc_worries_a_lot = self.psc_worries_a_lot or '0'
        psc_wants_to_be_with_parents = self.psc_wants_to_be_with_parents or '0'
        psc_feels_is_bad_child = self.psc_feels_is_bad_child or '0'
        psc_takes_unnecesary_risks = self.psc_takes_unnecesary_risks or '0'
        psc_gets_hurt_often = self.psc_gets_hurt_often or '0'
        psc_having_less_fun = self.psc_having_less_fun or '0'
        psc_act_as_younger = self.psc_act_as_younger or '0'
        psc_does_not_listen_to_rules = self.psc_does_not_listen_to_rules or '0'
        psc_does_not_show_feelings = self.psc_does_not_show_feelings or '0'
        psc_does_not_get_people_feelings = self.psc_does_not_get_people_feelings or '0'

        psc_teases_others = self.psc_teases_others or '0'
        psc_takes_things_from_others = self.psc_takes_things_from_others or '0'
        psc_refuses_to_share = self.psc_refuses_to_share or '0'
        v = {}
        psc_total = int(psc_aches_pains) + int(psc_spend_time_alone) + \
                    int(psc_tires_easily) + int(psc_fidgety) + \
                    int(psc_trouble_with_teacher) + \
                    int(psc_less_interest_in_school) + \
                    int(psc_acts_as_driven_by_motor) + \
                    int(psc_daydreams_too_much) + int(psc_distracted_easily) + \
                    int(psc_afraid_of_new_situations) + int(psc_sad_unhappy) + \
                    int(psc_irritable_angry) + int(psc_feels_hopeless) + \
                    int(psc_trouble_concentrating) + \
                    int(psc_less_interested_in_friends) + \
                    int(psc_fights_with_others) + int(psc_absent_from_school) + \
                    int(psc_school_grades_dropping) + int(psc_down_on_self) + \
                    int(psc_visit_doctor_finds_ok) + int(psc_trouble_sleeping) + \
                    int(psc_worries_a_lot) + int(psc_wants_to_be_with_parents) + \
                    int(psc_feels_is_bad_child) + int(psc_takes_unnecesary_risks) + \
                    int(psc_gets_hurt_often) + int(psc_having_less_fun) + \
                    int(psc_act_as_younger) + int(psc_does_not_listen_to_rules) + \
                    int(psc_does_not_show_feelings) + \
                    int(psc_does_not_get_people_feelings) + \
                    int(psc_teases_others) + \
                    int(psc_takes_things_from_others) + \
                    int(psc_refuses_to_share)
        self.psc_total = psc_total
#         v['psc_total'] = psc_total
#             
#         return {'value': v}
