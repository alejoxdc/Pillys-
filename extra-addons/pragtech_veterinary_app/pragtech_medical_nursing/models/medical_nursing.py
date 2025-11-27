import time
from odoo import api, fields, models, tools, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, RedirectWarning, ValidationError


@api.model
def _doctor_get(self):
    doc_ids = None
    partner_ids = self.env['res.partner'].search([('user_id', '=', self.env.user.id), ('is_doctor', '=', True)])
    if partner_ids:
        doc_ids = self.env['medical.physician'].search([('name', 'in', partner_ids)])
    return doc_ids


class medical_patient_rounding(models.Model):
    _name = "medical.patient.rounding"
    _description = 'Patient Rounding'

    name = fields.Many2one('medical.inpatient.registration', 'Registration Code', required=True)
    health_professional = fields.Many2one('medical.physician', 'Health Professional', readonly=True,
                                          default=_doctor_get)
    evaluation_start = fields.Datetime('Start', required=True, default=fields.Datetime.now)
    evaluation_end = fields.Datetime('End', required=True)
    environmental_assessment = fields.Char('Environment', size=256,
                                           help="Environment assessment . State any disorder in the room.")
    # The 6 P's of rounding
    pain = fields.Boolean('Pain', help="Check if the patient is in pain")
    pain_level = fields.Integer('Pain', help="Enter the pain level, from 1 to 10")
    potty = fields.Boolean('Potty', help="Check if the patient needs to urinate / defecate")
    position = fields.Boolean('Position', help="Check if the patient needs to be repositioned or is unconfortable")
    proximity = fields.Boolean('Proximity', help="Check if personal items, water, alarm, ... are not in easy reach")
    pump = fields.Boolean('Pumps', help="Check if there is any issues with the pumps - IVs ... ")
    personal_needs = fields.Boolean('Personal needs', help="Check if the patient requests anything")
    # Vital Signs
    systolic = fields.Integer('Systolic Pressure')
    diastolic = fields.Integer('Diastolic Pressure')
    bpm = fields.Integer('Heart Rate', help='Heart rate expressed in beats per minute')
    respiratory_rate = fields.Integer('Respiratory Rate', help='Respiratory rate expressed in breaths per minute')
    osat = fields.Integer('Oxygen Saturation', help='Oxygen Saturation(arterial).')
    temperature = fields.Float('Temperature', help='Temperature in celsius')
    # Diuresis
    diuresis = fields.Integer('Diuresis', help="volume in ml")
    urinary_catheter = fields.Boolean('Urinary Catheter')
    # Glycemia
    glycemia = fields.Integer('Glycemia', help='Blood Glucose level')
    depression = fields.Boolean('Depression signs', help="Check this if the patient shows signs of depression")
    evolution = fields.Selection([('n', 'Status Quo'), ('i', 'Improving'), ('w', 'Worsening'), ], 'Evolution',
                                 required=True,
                                 help="Check your judgement of current patient condition")
    round_summary = fields.Text('Round Summary')
    warning = fields.Boolean('Warning',
                             help="Check this box to alert the supervisor about this patient rounding. It will be shown in red in the rounding list")
    procedures = fields.One2many('medical.rounding_procedure', 'name', 'Procedures',
                                 help="List of the procedures in this rounding. Please enter the first one as the main procedure")


# one to many field Medication
# 'medicaments' : fields.One2many('medical.patient.rounding.medicament', 'name', 'Medicaments'),
# 'medical_supplies' : fields.One2many('medical.patient.rounding.medical_supply', 'name', 'Medical Supplies'),
# 'vaccines' : fields.One2many('medical.patient.rounding.vaccine', 'name', 'Vaccines'),
# one to many field Stock Moves
# moves : fields.One2many('stock.move', 'rounding', 'Stock Moves',readonly=True),

#     _defaults = {
#         'evaluation_start': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'), 
#         'health_professional' : _doctor_get,
#        }


class medical_rounding_procedure(models.Model):
    _name = "medical.rounding_procedure"
    _description = 'Rounding - Procedure'

    name = fields.Many2one('medical.patient.rounding', 'Rounding')
    procedure = fields.Many2one('medical.procedure', 'Code', required=True,
                                index=True,
                                help="Procedure Code, for example ICD-10-PCS Code 7-character string")
    notes = fields.Text('Notes')


class medical_patient_ambulatory_care(models.Model):
    _name = "medical.patient.ambulatory_care"
    _description = 'Patient Ambulatory Care'

    name = fields.Char('ID', size=256, readonly=True)
    patient = fields.Many2one('medical.patient', 'Patient', required=True)
    base_condition = fields.Many2one('medical.pathology', 'Base Condition')
    evaluation = fields.Many2one('medical.patient.evaluation', 'Related Evaluation', )
    ordering_professional = fields.Many2one('medical.physician', 'Ordering Physician')
    health_professional = fields.Many2one('medical.physician', 'Health Professional', readonly=True,
                                          default=_doctor_get)
    procedures = fields.One2many('medical.ambulatory_care_procedure', 'name', 'Procedures',
                                 help="List of the procedures in this session. Please enter the first one as the main procedure")
    session_number = fields.Integer('Session #', required=True)
    session_start = fields.Datetime('Start', required=True, default=fields.Datetime.now)
    # Vital Signs
    systolic = fields.Integer('Systolic Pressure')
    diastolic = fields.Integer('Diastolic Pressure')
    bpm = fields.Integer('Heart Rate', help='Heart rate expressed in beats per minute')
    respiratory_rate = fields.Integer('Respiratory Rate', help='Respiratory rate expressed in breaths per minute')
    osat = fields.Integer('Oxygen Saturation', help='Oxygen Saturation(arterial).')
    temperature = fields.Float('Temperature', help='Temperature in celsius')
    warning = fields.Boolean('Warning', help="Check this box to alert the "
                                             "supervisor about this session. It will be shown in red in the session list")
    # Glycemia
    glycemia = fields.Integer('Glycemia', help='Blood Glucose level')
    evolution = fields.Selection(
        [('initial', 'Initial'), ('n', 'Status Quo'), ('i', 'Improving'), ('w', 'Worsening'), ],
        'Evolution', required=True, help="Check your judgement of current patient condition", )
    session_end = fields.Datetime('End', required=True)
    next_session = fields.Datetime('Next Session')
    session_notes = fields.Text('Notes', required=True)

    # one to many field Medication
    # 'medicaments' : fields.One2many('medical.patient.ambulatory_care.medicament', 'name', 'Medicaments'),
    # 'medical_supplies' : fields.One2many('medical.patient.ambulatory_care.medical_supply', 'name', 'Medical Supplies'),
    # 'vaccines' : fields.One2many('medical.patient.ambulatory_care.vaccine', 'name', 'Vaccines'),
    # one to many field Stock Moves
    # moves = fields.One2many('stock.move', 'ambulatory_care', 'Stock Moves',readonly=True)

    #     _defaults = {
    #         'session_start': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
    #         'health_professional' : _doctor_get,
    #        }

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].get('medical.patient.ambulatory_care')
        return super(medical_patient_ambulatory_care, self).create(vals)


# medical_patient_ambulatory_care()

class medical_ambulatory_care_procedure(models.Model):
    _name = "medical.ambulatory_care_procedure"
    _description = 'Ambulatory Care Procedure'

    name = fields.Many2one('medical.patient.ambulatory_care', 'Session')
    procedure = fields.Many2one('medical.procedure', 'Code', required=True,
                                help="Procedure Code, for example ICD-10-PCS Code 7-Character string")
    comments = fields.Char('Comments', size=256)


# medical_ambulatory_care_procedure()

'''
class medical_patient_ambulatory_care_medicament(models.Model):
    _name = "medical.patient.ambulatory_care.medicament"
    _description = "Patient Ambulatory Care Medicament"

    _columns = {
    'name' : fields.many2one('medical.patient.ambulatory_care', 'Ambulatory ID'),
    'medicament' : fields.many2one('medical.medicament', 'Medicament'),
    'product' : fields.many2one('product.product', 'Product'),
    'quantity' : fields.Float('Quantity'),
    'short_comment' : fields.Many2one('Comment',
        help='Short comment on the specific drug'),
    }
    _defaults = {
	'quantity' : 1,
		}    

medical_patient_ambulatory_care_medicament()

class medical_patient_ambulatory_care_medical_supply(osv.osv):
    _name = "medical.patient.ambulatory_care.medical_supply"
    _description = "Patient Ambulatory Care Medical Supply"
    
    _columns = {
    
    'name' : fields.many2one('medical.patient.ambulatory_care', 'Ambulatory ID'),
    'product' : fields.many2one('product.product', 'Product'),
    'quantity' : fields.integer('Quantity'),
    'short_comment' : fields.char('Comment',
        help='Short comment on the specific drug'),
    }
    _defaults = {
	'quantity' : 1,
		} 

medical_patient_ambulatory_care_medical_supply()

class medical_patient_ambulatory_care_vaccine(osv.osv):
    _name = 'medical.patient.ambulatory_care.vaccine'
    _description = 'Patient Ambulatory Care Vaccine'

    _columns = {

#     'name' : fields.many2one('medical.patient.ambulatory_care', 'Ambulatory ID'),
#     'vaccine' : fields.many2one('product.product', 'Name', required=True),
#     'quantity' : fields.integer('Quantity'),
#     'dose' : fields.integer('Dose'),
#     'next_dose_date' : fields.datetime('Next Dose'),
#     'short_comment' : fields.char('Comment',
#         help='Short comment on the specific drug'),
    }
#     _defaults = {
# 	'quantity' : 1,
		} 

medical_patient_ambulatory_care_vaccine()


class medical_patient_rounding_medicament(osv.osv):
    _name = "medical.patient.rounding.medicament"
    _description = "Patient Rounding Medicament"

    _columns = {
    
#     'name' : fields.many2one('medical.patient.rounding', 'Ambulatory ID'),
#     'medicament' : fields.many2one('medical.medicament', 'Medicament'),
#     'product' : fields.many2one('product.product', 'Product'),
#     'quantity' : fields.integer('Quantity'),
#     'short_comment' : fields.char('Comment',
#         help='Short comment on the specific drug'),
    }
    _defaults = {
	'quantity' : 1,
		}    

medical_patient_rounding_medicament()

class medical_patient_rounding_medical_supply(osv.osv):
    _name = "medical.patient.rounding.medical_supply"
    _description = "Patient Rounding Medical Supply"
    
    _columns = {
    
    'name' : fields.many2one('medical.patient.rounding', 'Ambulatory ID'),
    'product' : fields.many2one('product.product', 'Product'),
    'quantity' : fields.integer('Quantity'),
    'short_comment' : fields.char('Comment',
        help='Short comment on the specific drug'),
    }
    _defaults = {
	'quantity' : 1,
		} 

medical_patient_rounding_medical_supply()

class medical_patient_rounding_vaccine(osv.osv):
    _name = 'medical.patient.rounding.vaccine'
    _description = 'Patient Rounding Vaccine'

    _columns = {

    'name' : fields.many2one('medical.patient.rounding', 'Ambulatory ID'),
    'vaccine' : fields.many2one('product.product', 'Name', required=True),
    'quantity' : fields.integer('Quantity'),
    'dose' : fields.integer('Dose'),
    'next_dose_date' : fields.datetime('Next Dose'),
    'short_comment' : fields.char('Comment',
        help='Short comment on the specific drug'),
    }
    _defaults = {
	'quantity' : 1,
		} 

medical_patient_rounding_vaccine()
'''
