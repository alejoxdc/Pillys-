# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
from datetime import datetime,timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, RedirectWarning, ValidationError
import time
import logging
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import hashlib
import pytz


class InsurancePlan(models.Model):
    _name = 'medical.insurance.plan'

    is_default = fields.Boolean(string='Default Plan',
                                help='Check if this is the default plan when assigning this insurance company to a patient')
    name = fields.Char(related='product_insurance_plan_id.name')
    product_insurance_plan_id = fields.Many2one('product.product', string='Plan', required=True,
                                                domain="[('type', '=', 'service'), ('is_insurance_plan', '=', True)]",
                                                help='Insurance company plan')

    company_id = fields.Many2one('res.partner', string='Insurance Company', required=True, domain="[('is_insurance_company', '=', '1')]")
    notes = fields.Text('Extra info')
    code = fields.Char(size=64, required=True, index=True)


class MedicalInsurance(models.Model):
    _name = "medical.insurance"

    @api.depends('number', 'company_id')
    def name_get(self):
        result = []
        for insurance in self:
            name = insurance.company_id.name + ':' + insurance.number
            result.append((insurance.id, name))
        return result

    name = fields.Char(related="res_partner_insurance_id.name")
    res_partner_insurance_id = fields.Many2one('res.partner', 'Owner', domain="[('is_owner', '=', True)]")
    number = fields.Char('Number', size=64, required=True)
    company_id = fields.Many2one('res.partner', 'Insurance Company', domain="[('is_insurance_company', '=', '1')]",
                                 required=True)
    member_since = fields.Date('Member since')
    member_exp = fields.Date('Expiration date')
    category = fields.Char('Category', size=64, help="Insurance company plan / category")
    type = fields.Selection([('state', 'State'), ('labour_union', 'Labour Union / Syndical'), ('private', 'Private'), ],
                            'Insurance Type')
    notes = fields.Text('Extra Info')
    plan_id = fields.Many2one('medical.insurance.plan', 'Plan', help='Insurance company plan')


class Partner(models.Model):
    _inherit = "res.partner"

    date = fields.Date('Partner since', help="Date of activation of the partner or patient")
    alias = fields.Char('alias', size=64)
    ref = fields.Char('ID Number')
    is_person = fields.Boolean('Person', help="Check if the partner is a person.")
    is_patient = fields.Boolean('Patient', help="Check if the partner is a patient")
    is_doctor = fields.Boolean('Doctor', help="Check if the partner is a doctor")
    is_institution = fields.Boolean('Institution', help="Check if the partner is a Medical Center")
    is_insurance_company = fields.Boolean('Insurance Company', help="Check if the partner is a Insurance Company")
    is_pharmacy = fields.Boolean('Pharmacy', help="Check if the partner is a Pharmacy")
    lastname = fields.Char('Last Name', size=128, help="Last Name")
    insurance_ids = fields.One2many('medical.insurance', 'name', "Insurance")
    user_id1 = fields.Many2one('res.users', 'Internal User',
                               help='In Medical is the user (doctor, nurse) that logins into OpenERP that will relate to the patient or family. When the partner is a doctor or a health proffesional, it will be the user that maps the doctor\'s partner name. It must be present.')

    _sql_constraints = [('ref_uniq', 'unique (ref)', 'The partner or patient code must be unique')]

    @api.depends('name', 'lastname')
    def name_get(self):
        result = []
        for partner in self:
            name = partner.name
            if partner.lastname:
                name = partner.lastname + ', ' + name
            result.append((partner.id, name))
        return result


class ProductProduct(models.Model):
    _inherit = "product.product"

    is_medicament = fields.Boolean('Medicament', help="Check if the product is a medicament")
    is_vaccine = fields.Boolean('Vaccine', help="Check if the product is a vaccine")
    is_bed = fields.Boolean('Bed', help="Check if the product is a bed on the medical center")
    is_insurance_plan = fields.Boolean('Insurance Plan', help='Check if the product is an insurance plan')
    is_medical_supply = fields.Boolean('Medical Supply', help='Check if the product is a medical supply')


class MedicalProcedure(models.Model):
    _description = "Medical Procedure"
    _name = "medical.procedure"

    name = fields.Char('Code', size=128, required=True)
    description = fields.Char('Long Text', size=256)

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search(['|', ('name', operator, name), ('description', operator, name)])
        if not recs:
            recs = self.search([('name', operator, name)])
        return recs.name_get()


class PathologyCategory(models.Model):
    _description = 'Disease Categories'
    _name = 'medical.pathology.category'
    _order = 'parent_id,id'

    @api.depends('name', 'parent_id')
    def name_get(self):
        result = []
        for partner in self:
            name = partner.name
            if partner.parent_id:
                name = partner.parent_id.name + ' / ' + name
            result.append((partner.id, name))
        return result

    #     @api.model
    #     def _name_get_fnc(self):
    #         res = self._name_get_fnc()
    #         return res

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('Error ! You cannot create a recursive category.'))

    name = fields.Char('Category Name', required=True, size=128)
    parent_id = fields.Many2one('medical.pathology.category', 'Parent Category', index=True)
    complete_name = fields.Char(string="Name")
    child_ids = fields.One2many('medical.pathology.category', 'parent_id', 'Children Category')
    active = fields.Boolean('Active', default=True, )


#     _constraints = [
#         (_check_parent_id, 'Error ! You can not create recursive categories.', ['parent_id'])
#     ]

class MedicalPathology(models.Model):
    _name = "medical.pathology"
    _description = "Diseases"

    name = fields.Char('Name', required=True, size=128, help="Disease name")
    code = fields.Char('Code', size=32, required=True, help="Specific Code for the Disease (eg, ICD-10, SNOMED...)")
    category = fields.Many2one('medical.pathology.category', 'Disease Category')
    chromosome = fields.Char('Affected Chromosome', size=128, help="chromosome number")
    protein = fields.Char('Protein involved', size=128, help="Name of the protein(s) affected")
    gene = fields.Char('Gene', size=128, help="Name of the gene(s) affected")
    info = fields.Text('Extra Info')
    line_ids = fields.One2many('medical.pathology.group.member', 'name',
                               'Groups', help='Specify the groups this pathology belongs. Some'
                                              ' automated processes act upon the code of the group')

    _sql_constraints = [('code_uniq', 'unique (code)', 'The disease code must be unique')]

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search(['|', ('name', operator, name), ('code', operator, name)])
        if not recs:
            recs = self.search([('name', operator, name)])
        return recs.name_get()


class MedicalPathologyGroup(models.Model):
    _description = 'Pathology Group'
    _name = 'medical.pathology.group'

    name = fields.Char('Name', required=True, translate=True, help='Group name')
    code = fields.Char('Code', size=128, required=True,
                       help='for example MDG6 code will contain the Millennium Development'
                            ' Goals # 6 diseases : Tuberculosis, Malaria and HIV/AIDS')
    desc = fields.Char('Short Description', size=128, required=True)
    info = fields.Text('Detailed information')


class MedicalPathologyGroupMember(models.Model):
    _description = 'Pathology Group Member'
    _name = 'medical.pathology.group.member'

    name = fields.Many2one('medical.pathology', 'Disease', readonly=True)
    disease_group = fields.Many2one('medical.pathology.group', 'Group', required=True)


class MedicamentCategory(models.Model):
    _description = 'Medicament Categories'
    _name = 'medicament.category'
    _order = 'parent_id,id'

    @api.depends('name', 'parent_id')
    def name_get(self):
        result = []
        for partner in self:
            name = partner.name
            if partner.parent_id:
                name = partner.parent_id.name + ' / ' + name
            result.append((partner.id, name))
        return result

    @api.model
    def _name_get_fnc(self):
        res = self._name_get_fnc()
        return res

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('Error ! You cannot create a recursive category.'))

    name = fields.Char('Category Name', required=True, size=128)
    parent_id = fields.Many2one('medicament.category', 'Parent Category', index=True)
    complete_name = fields.Char(compute='_name_get_fnc', string="Name")
    child_ids = fields.One2many('medicament.category', 'parent_id', 'Children Category')


#     _constraints = [
#             (_check_parent_id, 'Error ! You can not create recursive categories.', ['parent_id'])
#     ]

class MedicalMedicament(models.Model):
    _description = 'Medicament'
    _name = "medical.medicament"

    name = fields.Char(related="product_medicament_id.name")
    product_medicament_id = fields.Many2one('product.product', 'Name', required=True,
                                            domain=[('is_medicament', '=', "1")], help="Commercial Name")

    category = fields.Many2one('medicament.category', 'Category')
    active_component = fields.Char('Active component', size=128, help="Active Component")
    therapeutic_action = fields.Char('Therapeutic effect', size=128, help="Therapeutic action")
    composition = fields.Text('Composition', help="Components")
    indications = fields.Text('Indication', help="Indications")
    dosage = fields.Text('Dosage Instructions', help="Dosage / Indications")
    overdosage = fields.Text('Overdosage', help="Overdosage")
    pregnancy_warning = fields.Boolean('Pregnancy Warning',
                                       help="Check when the drug can not be taken during pregnancy or lactancy")
    pregnancy = fields.Text('Pregnancy and Lactancy', help="Warnings for Pregnant Women")
    presentation = fields.Text('Presentation', help="Packaging")
    adverse_reaction = fields.Text('Adverse Reactions')
    storage = fields.Text('Storage Conditions')
    price = fields.Float(related='product_medicament_id.lst_price', string='Price')
    qty_available = fields.Float(related='product_medicament_id.qty_available', string='Quantity Available')
    notes = fields.Text('Extra Info')
    pregnancy_category = fields.Selection([
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
        ('X', 'X'),
        ('N', 'N')], 'Pregnancy Category',
        help='** FDA Pregancy Categories ***\n'
             'CATEGORY A :Adequate and well-controlled human studies have failed'
             ' to demonstrate a risk to the fetus in the first trimester of'
             ' pregnancy (and there is no evidence of risk in later'
             ' trimesters).\n\n'
             'CATEGORY B : Animal reproduction studies have failed todemonstrate a'
             ' risk to the fetus and there are no adequate and well-controlled'
             ' studies in pregnant women OR Animal studies have shown an adverse'
             ' effect, but adequate and well-controlled studies in pregnant women'
             ' have failed to demonstrate a risk to the fetus in any'
             ' trimester.\n\n'
             'CATEGORY C : Animal reproduction studies have shown an adverse'
             ' effect on the fetus and there are no adequate and well-controlled'
             ' studies in humans, but potential benefits may warrant use of the'
             ' drug in pregnant women despite potential risks. \n\n '
             'CATEGORY D : There is positive evidence of human fetal  risk based'
             ' on adverse reaction data from investigational or marketing'
             ' experience or studies in humans, but potential benefits may warrant'
             ' use of the drug in pregnant women despite potential risks.\n\n'
             'CATEGORY X : Studies in animals or humans have demonstrated fetal'
             ' abnormalities and/or there is positive evidence of human fetal risk'
             ' based on adverse reaction data from investigational or marketing'
             ' experience, and the risks involved in use of the drug in pregnant'
             ' women clearly outweigh potential benefits.\n\n'
             'CATEGORY N : Not yet classified')


class MedicalOperationalArea(models.Model):
    _description = 'Operational Area'
    _name = "medical.operational_area"

    name = fields.Char('Name', size=128, required=True, help="Operational Area of the city or region")
    operational_sector = fields.One2many('medical.operational_sector', 'operational_area', 'Operational Sector', readonly=True)
    info = fields.Text('Extra Information')

    _sql_constraints = [('code_uniq', 'unique (name)', 'The Operational Area code name must be unique')]


class MedicalOperationalSector(models.Model):
    _name = "medical.operational_sector"

    name = fields.Char('Name', size=128, required=True, help="Region included in an operational area")
    operational_area = fields.Many2one('medical.operational_area', 'Operational Area')
    info = fields.Text('Extra Information')

    _sql_constraints = [
        ('code_uniq', 'unique (name,operational_area)',
         'The Operational Sector code and OP Area combination must be unique')]


class MedicalFamilyCode(models.Model):
    _name = "medical.family_code"

    name = fields.Char(related="res_partner_family_medical_id.name")
    res_partner_family_medical_id = fields.Many2one('res.partner', 'Name', required=True,
                                                    help="Family code within an operational sector")
    operational_sector = fields.Many2one('medical.operational_sector', 'Operational Sector')
    members_ids = fields.Many2many('res.partner', 'family_members_rel', 'family_id', 'members_id', 'Members',
                                   domain=[('is_person', '=', "1")])
    info = fields.Text('Extra Information')

    _sql_constraints = [('code_uniq', 'unique (res_partner_family_medical_id)', 'The Family code name must be unique')]


class MedicalSpeciality(models.Model):
    _name = "medical.speciality"

    name = fields.Char('Description', size=128, required=True, help="ie, Addiction Psychiatry")
    code = fields.Char('Code', size=128, help="ie, ADP")

    _sql_constraints = [('code_uniq', 'unique (name)', 'The Medical Specialty code must be unique')]


class MedicalPhysician(models.Model):
    _name = "medical.physician"
    _description = "Information about the doctor"

    name = fields.Char(related="res_partner_physician_id.name")
    res_partner_physician_id = fields.Many2one('res.partner', 'Physician', required=True,
                                               domain=[('is_doctor', '=', "1"), ('is_person', '=', "1")],
                                               help="Physician's Name, from the partner list")
    institution = fields.Many2one('res.partner', 'Institution', domain=[('is_institution', '=', "1")],
                                  help="Institution where she/he works")
    code = fields.Char('ID', size=128, help="MD License ID")
    speciality = fields.Many2one('medical.speciality', 'Specialty', required=True, help="Specialty Code")
    info = fields.Text('Extra info')
    user_id = fields.Many2one('res.users', related='res_partner_physician_id.user_id', string='Physician User', store=True)
    email = fields.Char('Email')
    mobile = fields.Char('Mobile')
    slot_ids = fields.One2many('doctor.slot', 'doctor_id', 'Availabilities', copy=True)


class MedicalEthnicGroup(models.Model):
    _name = "medical.ethnicity"

    name = fields.Char('Ethnic group', size=128, required=True)
    code = fields.Char('Code', size=64)

    _sql_constraints = [('ethnic_name_uniq', 'unique(name)', 'The Name must be unique !')]


class MedicalOccupation(models.Model):
    _name = "medical.occupation"
    _description = "Occupation / Job"

    name = fields.Char('Occupation', size=128, required=True)
    code = fields.Char('Code', size=64)

    _sql_constraints = [('occupation_name_uniq', 'unique(name)', 'The Name must be unique !')]


class MedicalDoseUnit(models.Model):
    _name = "medical.dose.unit"

    name = fields.Char('Unit', size=32, required=True, )
    desc = fields.Char('Description', size=64)

    _sql_constraints = [('dose_name_uniq', 'unique(name)', 'The Unit must be unique !')]


class MedicalDrugRoute(models.Model):
    _name = "medical.drug.route"

    name = fields.Char('Route', size=64, required=True)
    code = fields.Char('Code', size=32)

    _sql_constraints = [('route_name_uniq', 'unique(name)', 'The Name must be unique !')]


class MedicalDrugForm(models.Model):
    _name = "medical.drug.form"

    name = fields.Char('Form', size=64, required=True, )
    code = fields.Char('Code', size=32)

    _sql_constraints = [('drug_name_uniq', 'unique(name)', 'The Name must be unique !')]


# PATIENT GENERAL INFORMATION

class MedicalPatient(models.Model):

    # @api.depends('partner_id', 'patient_id')
    # def name_get(self):
    #     result = []
    #     for partner in self:
    #         name = partner.partner_id.name
    #         if partner.patient_id:
    #             name = '[' + partner.patient_id + ']' + name
    #         result.append((partner.id, name))
    #     return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search(['|', ('partner_id', operator, name), ('patient_id', operator, name)])
        if not recs:
            recs = self.search([('partner_id', operator, name)])
        return recs.name_get()

    @api.onchange('dob')
    def onchange_dob(self):
        c_date = datetime.today().strftime('%Y-%m-%d')
        # if self.dob:
            # print("\n\nself.dob=====================", type(self.dob))
            # print("\n\nc_date====================", type(c_date))
        return {}

    # Automatically assign the family code

    @api.onchange('partner_id')
    def onchange_partnerid(self):
        family_code_id = ""
        if self.partner_id:
            self.current_address = self.partner_id
            self._cr.execute('select family_id from family_members_rel where members_id=%s limit 1', (self.partner_id.id,))
            a = self._cr.fetchone()
            if a:
                family_code_id = a[0]
            else:
                family_code_id = ''
        self.family_code = family_code_id

    # Get the patient age in the following format : "YEARS MONTHS DAYS"
    # It will calculate the age of the patient while the patient is alive. When the patient dies, it will show the age at time of death.

    def _patient_age(self):
        self.partner_id.owner_name = self.current_address.id
        def compute_age_from_dates(patient_dob, patient_deceased, patient_dod):
            now = datetime.now()
            if (patient_dob):
                dob = datetime.strptime(str(patient_dob), '%Y-%m-%d')
                if patient_deceased:
                    dod = datetime.strptime(patient_dod, '%Y-%m-%d %H:%M:%S')
                    delta = relativedelta(dod, dob)
                    deceased = " (deceased)"
                else:
                    delta = relativedelta(now, dob)
                    deceased = ''
                years_months_days = str(delta.years) + "y " + str(delta.months) + "m " + str(
                    delta.days) + "d" + deceased
            else:
                years_months_days = "No DoB !"

            return years_months_days

        self.age = compute_age_from_dates(self.dob, self.deceased, self.dod)

    _name = "medical.patient"
    _description = "Patient related information"
    _rec_name = 'partner_id'

    partner_id = fields.Many2one('res.partner', 'Patient', required="1", domain=[('is_patient', '=', True), ('is_person', '=', True)], help="Patient Name")
    patient_id = fields.Char('ID', required=True, index=True,
                             help="Patient Identifier provided by the Health Center. Is not the patient id from the partner form",
                             default=lambda self: _('New'))
    lastname = fields.Char(related='partner_id.lastname', string='Lastname')
    family_code = fields.Many2one('medical.family_code', 'Family', help="Family Code")
    identifier = fields.Char(string='SSN', related='partner_id.ref', help="Social Security Number or National ID")
    current_insurance = fields.Many2one('medical.insurance', "Insurance", domain="[('res_partner_insurance_id','=',partner_id)]",
                                        help="Insurance information. You may choose from the different insurances belonging to the patient")
    current_address = fields.Many2one('res.partner', "Owner Details",
                                      help="Contact information. You may choose from the different contacts and addresses this patient has")
    primary_care_doctor = fields.Many2one('medical.physician', 'Primary Care Doctor', help="Current primary care / family doctor")
    photo = fields.Binary(string='Picture')
    dob = fields.Date('Date of Birth')
    age = fields.Char(compute='_patient_age', string='Patient Age',
                      help="It shows the age of the patient in years(y), months(m) and days(d).\nIf the patient has died, the age shown is the age at time of death, the age corresponding to the date on the death certificate. It will show also \"deceased\" on the field")
    sex = fields.Selection([
        ('m', 'Male'),
        ('f', 'Female')], 'Sex', index=True)
    marital_status = fields.Selection([
        ('s', 'Single'),
        ('m', 'Married'),
        ('w', 'Widowed'),
        ('d', 'Divorced'),
        ('x', 'Separated')], 'Marital Status')
    blood_type = fields.Selection([
        ('A', 'A'),
        ('B', 'B'),
        ('AB', 'AB'),
        ('O', 'O')], 'Blood Type')
    rh = fields.Selection([('+', '+'), ('-', '-')], 'Rh')
    pet_blood_group = fields.Many2one('pet.blood.group', 'Pet Blood Group')
    user_id = fields.Many2one('res.users', related='partner_id.user_id', string='Doctor',
                              help="Physician that logs in the local Medical system (HIS), on the health center. It doesn't necesarily has do be the same as the Primary Care doctor",
                              store=True)
    ethnic_group = fields.Many2one('medical.ethnicity', 'Ethnic group')
    vaccinations = fields.One2many('medical.vaccination', 'name', "Vaccinations")
    medications = fields.One2many('medical.patient.medication', 'name', 'Medications')
    prescriptions = fields.One2many('medical.prescription.order', 'name', "Prescriptions")
    diseases = fields.One2many('medical.patient.disease', 'name', 'Diseases')
    critical_info = fields.Text('Important disease, allergy or procedures information',
                                help="Write any important information on the patient's disease, surgeries, allergies, ...")
    evaluation_ids = fields.One2many('medical.patient.evaluation', 'name', 'Evaluation')
    general_info = fields.Text('General Information', help="General information about the patient")
    deceased = fields.Boolean('Deceased', help="Mark if the patient has died")
    dod = fields.Datetime('Date of Death')
    cod = fields.Many2one('medical.pathology', 'Cause of Death')
    apt_id = fields.Many2many('medical.appointment', 'pat_apt_rel', 'patient', 'apid', )
    childbearing_age = fields.Char(compute='_patient_age', string='Potential for Childbearing')
    report_date = fields.Datetime("Report Date:", default=fields.Datetime.now)

    _sql_constraints = [('name_uniq', 'unique (partner_id)', 'The Patient already exists')]

    def name_get(self):
        result = []
        for partner in self:
            if partner:
                # print("Patient Name  ",partner.partner_id.name)
                name = partner.partner_id.name
                result.append((partner.id, name))
        return result

    @api.model
    def name_create(self, name):
        partner_id = self.env['res.partner'].sudo().create({
            'name': name,
            'is_patient': True,
            'is_person': True})
        medical_partner_id = self.create({'name': partner_id.id})
        return [(self.id)]

    @api.model
    def create(self, vals):
        if vals.get('patient_id', 'New') == 'New':
            vals['patient_id'] = self.env['ir.sequence'].next_by_code('medical.patient') or 'New'
        result = super(MedicalPatient, self).create(vals)
        return result
    

class MedicalAppointment(models.Model):
    _name = "medical.appointment"
    _order = "appointment_sdate desc"

    @api.model
    def _get_default_doctor(self):
        doc_ids = None
        partner_ids = self.env['res.partner'].search([('user_id', '=', self.env.user.id), ('is_doctor', '=', True)])
        if partner_ids:
            doc_ids = self.env['medical.physician'].search([('res_partner_physician_id', 'in', partner_ids.ids)])
        return doc_ids

    doctor = fields.Many2one('medical.physician', 'Physician', help="Physician's Name", default=_get_default_doctor,required=True)
    name = fields.Char('Appointment ID', size=64, readonly=True, default=lambda self: _('New'))
    patient = fields.Many2one('medical.patient', 'Patient', help="Patient Name", required=True, )
    appointment_sdate = fields.Datetime('Appointment Start', required=True, default=fields.Datetime.now)
    appointment_edate = fields.Datetime('Appointment End')
    institution = fields.Many2one('res.partner', 'Health Center', domain=[('is_institution', '=', "1")], help="Medical Center")
    speciality = fields.Many2one('medical.speciality', 'Speciality', )
    urgency = fields.Selection([
        ('a', 'Normal'),
        ('b', 'Urgent'),
        ('c', 'Medical Emergency')], 'Urgency Level', default='a')
    comments = fields.Text('Comments')
    user_id = fields.Many2one('res.users', related='doctor.user_id', string='Physician', store=True)
    patient_status = fields.Selection([
        ('ambulatory', 'Ambulatory'),
        ('outpatient', 'Outpatient'),
        ('inpatient', 'Inpatient')], 'Patient status', default='ambulatory')
    inv_id = fields.Many2one('account.move', 'Invoice', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancel', 'Cancel')], 'State', readonly="1", default='draft')
    apt_id = fields.Boolean(default=False)
    app_hour = fields.Many2one("hour.select", string="Hours")
    app_minute = fields.Many2one("minute.select", string="Minute")

    _sql_constraints = [
        ('date_check', "CHECK (appointment_sdate <= appointment_edate)",
         "Appointment Start Date must be before Appointment End Date !")]

    # @api.one
    # def get_date(self,date1,lang):
    #      new_date=''
    #     if date1:
    #         search_id = self.env['res.lang'].search([('code','=',lang)])
    #         new_date=datetime.strftime(datetime.strptime(date1,'%Y-%m-%d %H:%M:%S').date(),record.date_format)
    #      return new_date

    #     def get_date(self, cr, uid, ids, date1,lang):
    #         new_date=''
    #         if date1:
    #             search_id = self.pool.get('res.lang').search(cr,uid,[('code','=',lang)])
    #             record=self.pool.get('res.lang').browse(cr,uid,search_id)
    #             new_date=datetime.strftime(datetime.strptime(date1,'%Y-%m-%d %H:%M:%S').date(),record.date_format)
    #         return new_date

    def action_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    @api.onchange('doctor')
    def onchange_doctor(self):
        family_code_id = ""
        if self.doctor:
            self.speciality = self.doctor.speciality

    def write(self, vals):
        for appointmnet in self.search([]):
            now = datetime.now()
            if vals.get('appointment_sdate') and str(vals['appointment_sdate']) < str(now)[0:19]:
                raise ValidationError(_('Start of Appointment Date is back date.'))
            if appointmnet.doctor.id == vals.get('doctor'):
                if 'appointment_sdate' in vals:
                    app_sdate = vals.get('appointment_sdate')
                else:
                    app_sdate = self.appointment_sdate
                if 'appointment_edate' in vals:
                    app_edate = vals.get('appointment_edate')
                else:
                    app_edate = self.appointment_edate

                start_date = datetime.strptime(str(app_sdate), '%Y-%m-%d %H:%M:%S')
                end_date = datetime.strptime(str(app_edate), '%Y-%m-%d %H:%M:%S')

                if appointmnet.appointment_sdate >= start_date and end_date <= appointmnet.appointment_edate:
                    raise ValidationError(_('Appointment Overlapping.'))

                if appointmnet.appointment_sdate <= start_date and appointmnet.appointment_edate >= start_date:
                    raise ValidationError(_('Appointment Overlapping.'))

                if appointmnet.appointment_sdate <= end_date and appointmnet.appointment_edate >= end_date:
                    raise ValidationError(_('Appointment Overlapping.'))

                if appointmnet.appointment_sdate >= start_date and appointmnet.appointment_edate <= end_date:
                    raise ValidationError(_('Appointment Overlapping.'))

                if start_date >= end_date:
                    raise ValidationError(_('Start of Appointment Date is greater than End of Appointment Date.'))
        result = super(MedicalAppointment, self).write(vals)
        return result

    @api.model
    def create(self, vals):
        for appointmnet in self.search([]):
            now = datetime.now()

            if vals.get('appointment_sdate') and str(vals['appointment_sdate']) < str(now)[0:19]:
                raise ValidationError(_('Start of Appointment Date is back date.'))
            if appointmnet.doctor.id == vals['doctor']:
                app_sdate = vals['appointment_sdate']
                app_edate = vals['appointment_edate']

                start_date = datetime.strptime(str(app_sdate), '%Y-%m-%d %H:%M:%S')
                end_date = datetime.strptime(str(app_edate), '%Y-%m-%d %H:%M:%S')

                if appointmnet.appointment_sdate <= start_date and end_date <= appointmnet.appointment_edate:
                    raise ValidationError(_('Appointment Overlapping.'))

                if appointmnet.appointment_sdate <= start_date and appointmnet.appointment_edate >= start_date:
                    raise ValidationError(_('Appointment Overlapping.'))

                if appointmnet.appointment_sdate <= end_date and appointmnet.appointment_edate >= end_date:
                    raise ValidationError(_('Appointment Overlapping.'))

                if appointmnet.appointment_sdate >= start_date and appointmnet.appointment_edate <= end_date:
                    raise ValidationError(_('Appointment Overlapping.'))

                if start_date >= end_date:
                    raise ValidationError(_('Start of Appointment Date is greater than End of Appointment Date.'))

        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('medical.appointment') or 'New'

        result = super(MedicalAppointment, self).create(vals)
        self._cr.execute('insert into pat_apt_rel(patient,apid) values (%s,%s)', (vals['patient'], result.id))
        return result

    @api.onchange('appointment_sdate', 'appointment_edate','doctor')
    def onchange_doctor(self):
        try:
            if self.appointment_sdate:
                doctors = self.env['medical.physician'].sudo().search([])
                doctor_list = []
                doc_without_slot = doctors.filtered(lambda x: len(x.slot_ids) == 0)
                for doctor in doctors:
                    for slot in doctor.sudo().slot_ids:
                        if slot.weekday == str(self.appointment_sdate.weekday()):

                            user_tz = self.env.user.tz or pytz.utc
                            local = pytz.timezone(user_tz)
                            display_date_result = datetime.strftime(
                                pytz.utc.localize(self.appointment_sdate,
                                                  DEFAULT_SERVER_DATETIME_FORMAT).astimezone(
                                    local), "%m/%d/%Y %H:%M:%S")
                            datetime_object = datetime.strptime(display_date_result, '%m/%d/%Y %H:%M:%S')
                            timefloat_start = datetime_object.time().strftime("%H:%M")
                            display_date_result = datetime.strftime(
                                pytz.utc.localize(self.appointment_edate,
                                                  DEFAULT_SERVER_DATETIME_FORMAT).astimezone(
                                    local), "%m/%d/%Y %H:%M:%S")
                            datetime_object = datetime.strptime(display_date_result, '%m/%d/%Y %H:%M:%S')
                            timefloat_end = datetime_object.time().strftime("%H:%M")
                            start_hour = '{0:02.0f}:{1:02.0f}'.format(*divmod(slot.start_hour * 60, 60))
                            end_hour = '{0:02.0f}:{1:02.0f}'.format(*divmod(slot.end_hour * 60, 60))

                            if timefloat_start >= start_hour and end_hour >= timefloat_end:
                                doctor_list.append(doctor.id)

                for doc in doc_without_slot:
                    doctor_list.append(doc.id)

                return {'domain': {'doctor': [('id', 'in', doctor_list)]}}

        except:
            return {'domain': {'doctor': []}}

    @api.onchange('app_hour', 'app_minute', 'appointment_sdate')
    def onchange_app_hour(self):
        minutes = self.app_minute.name or 0
        hours = (self.app_hour.name * 60) or 0
        total_minutes = minutes + hours
        hours_added = timedelta(minutes=total_minutes)
        end_datetime = self.appointment_sdate + hours_added
        self.appointment_edate = end_datetime


class HourSelect(models.Model):
    _name = "hour.select"
    name = fields.Integer("Name")


class MinuteSelect(models.Model):
    _name = "minute.select"
    name = fields.Integer("Name")


class MedicalPatientDisease(models.Model):

    @api.depends('pathology')
    def name_get(self):
        result = []
        for disease in self:
            name = disease.pathology.name
            result.append((disease.id, name))
        return result

    _name = "medical.patient.disease"
    _description = "Disease info"
    _order = 'is_active desc, disease_severity desc, is_infectious desc, is_allergy desc, diagnosed_date desc'

    name = fields.Many2one('medical.patient', 'Patient ID', readonly=True)
    pathology = fields.Many2one('medical.pathology', 'Disease', required=True, help="Disease")
    disease_severity = fields.Selection([
        ('1_mi', 'Mild'),
        ('2_mo', 'Moderate'),
        ('3_sv', 'Severe')], 'Severity', index=True)
    is_on_treatment = fields.Boolean('Currently on Treatment')
    is_infectious = fields.Boolean('Infectious Disease',
                                   help="Check if the patient has an infectious / transmissible disease")
    short_comment = fields.Char('Remarks', size=128,
                                help="Brief, one-line remark of the disease. Longer description will go on the Extra info field")
    doctor = fields.Many2one('medical.physician', 'Physician', help="Physician who treated or diagnosed the patient")
    diagnosed_date = fields.Date('Date of Diagnosis')
    healed_date = fields.Date('Healed')
    is_active = fields.Boolean('Active disease', default=True)
    age = fields.Integer('Age when diagnosed', help='Patient age at the moment of the diagnosis. Can be estimative')
    pregnancy_warning = fields.Boolean('Pregnancy warning')
    weeks_of_pregnancy = fields.Integer('Contracted in pregnancy week #')
    is_allergy = fields.Boolean('Allergic Disease')
    allergy_type = fields.Selection([
        ('da', 'Drug Allergy'),
        ('fa', 'Food Allergy'),
        ('ma', 'Misc Allergy'),
        ('mc', 'Misc Contraindication')], 'Allergy type', index=True)
    pcs_code = fields.Many2one('medical.procedure', 'Code', help="Procedure code, for example, ICD-10-PCS Code 7-character string")
    treatment_description = fields.Char('Treatment Description', size=128)
    date_start_treatment = fields.Date('Start of treatment')
    date_stop_treatment = fields.Date('End of treatment')
    status = fields.Selection([
        ('c', 'chronic'),
        ('s', 'status quo'),
        ('h', 'healed'),
        ('i', 'improving'),
        ('w', 'worsening')], 'Status of the disease')
    extra_info = fields.Text('Extra Info')

    _sql_constraints = [
        ('validate_disease_period', "CHECK (diagnosed_date < healed_date )",
         "DIAGNOSED Date must be before HEALED Date !"),
        ('end_treatment_date_before_start', "CHECK (date_start_treatment < date_stop_treatment )",
         "Treatment start Date must be before Treatment end Date !")]


# MEDICATION DOSAGE
class MedicalMedicationDosage(models.Model):
    _name = "medical.medication.dosage"
    _description = "Medicament Common Dosage combinations"

    name = fields.Char('Frequency', size=256, help='Common frequency name', required=True)
    code = fields.Char('Code', size=64, help='Dosage Code, such as SNOMED, 229798009 = 3 times per day')
    abbreviation = fields.Char('Abbreviation', size=64,
                               help='Dosage abbreviation, such as tid in the US or tds in the UK')

    _sql_constraints = [('name_uniq', 'unique (name)', 'The Unit already exists')]


# MEDICATION TEMPLATE
# TEMPLATE USED IN MEDICATION AND PRESCRIPTION ORDERS

class MedicalMedicationTemplate(models.Model):
    _name = "medical.medication.template"
    _description = "Template for medication"

    medicament = fields.Many2one('medical.medicament', 'Medicament', help="Prescribed Medicament", required=True, )
    indication = fields.Many2one('medical.pathology', 'Indication',
                                 help="Choose a disease for this medicament from the disease list. It can be an existing disease of the patient or a prophylactic.")
    dose = fields.Float('Dose', help="Amount of medication (eg, 250 mg ) each time the patient takes it")
    dose_unit = fields.Many2one('medical.dose.unit', 'dose unit', help="Unit of measure for the medication to be taken")
    route = fields.Many2one('medical.drug.route', 'Administration Route', help="HL7 or other standard drug administration route code.")
    form = fields.Many2one('medical.drug.form', 'Form', help="Drug form, such as tablet or gel")
    qty = fields.Integer('x', default=1, help="Quantity of units (eg, 2 capsules) of the medicament")
    common_dosage = fields.Many2one('medical.medication.dosage', 'Frequency', help="Common / standard dosage frequency for this medicament")
    frequency = fields.Integer('Frequency', help="Time in between doses the patient must wait (ie, for 1 pill each 8 hours, put here 8 and select 'hours' in the unit field")
    frequency_unit = fields.Selection([
        ('seconds', 'seconds'),
        ('minutes', 'minutes'),
        ('hours', 'hours'),
        ('days', 'days'),
        ('weeks', 'weeks'),
        ('wr', 'when required')], 'unit', index=True, default='hours')
    admin_times = fields.Char('Admin hours', size=128,
                              help='Suggested administration hours. For example, at 08:00, 13:00 and 18:00 can be encoded like 08 13 18')
    duration = fields.Integer('Treatment duration',
                              help="Period that the patient must take the medication. in minutes, hours, days, months, years or indefinately")
    duration_period = fields.Selection([
        ('minutes', 'minutes'),
        ('hours', 'hours'),
        ('days', 'days'),
        ('months', 'months'),
        ('years', 'years'),
        ('indefinite', 'indefinite')], 'Treatment Period', default='days',
        help="Period that the patient must take the medication. in minutes, hours, days, months, years or indefinately")
    start_treatment = fields.Datetime('Start of treatment', default=fields.Datetime.now)
    end_treatment = fields.Datetime('End of treatment')

    _sql_constraints = [
        ('dates_check', "CHECK (start_treatment < end_treatment)",
         "Treatment Star Date must be before Treatment End Date !")]


# PATIENT MEDICATION TREATMENT
class MedicalPatientMedication(models.Model):
    _name = "medical.patient.medication"
    _inherits = {'medical.medication.template': 'template'}
    _description = "Patient Medication"

    template = fields.Many2one('medical.medication.template', 'Template ID', required=True, index=True, ondelete="cascade")
    name = fields.Many2one('medical.patient', 'Patient ID', readonly=True)
    doctor = fields.Many2one('medical.physician', 'Physician', help="Physician who prescribed the medicament")
    is_active = fields.Boolean('Active', default=True,
                               help="Check this option if the patient is currently taking the medication")
    discontinued = fields.Boolean('Discontinued')
    course_completed = fields.Boolean('Course Completed')
    discontinued_reason = fields.Char('Reason for discontinuation', size=128, help="Short description for discontinuing the treatment")
    adverse_reaction = fields.Text('Adverse Reactions', help="Specific side effects or adverse reactions that the patient experienced")
    notes = fields.Text('Extra Info')
    patient_id = fields.Many2one('medical.patient', 'Patient')

    @api.onchange('course_completed', 'discontinued', 'is_active')
    def onchange_medication(self):
        family_code_id = ""
        if self.course_completed:
            self.is_active = False
            self.discontinued = False
        elif self.is_active == False and self.discontinued == False and self.course_completed == False:
            self.is_active = True
        if self.discontinued:
            self.is_active = False
            self.course_completed = False
        elif self.is_active == False and self.discontinued == False and self.course_completed == False:
            self.is_active = True
        if self.is_active == True:
            self.course_completed = False
            self.discontinued = False
        elif self.is_active == False and self.discontinued == False and self.course_completed == False:
            self.course_completed = True


# # PATIENT EVALUATION
class MedicalPatientEvaluation(models.Model):
    _name = "medical.patient.evaluation"
    _description = "evaluation"

    @api.model
    def _get_default_doctor(self):
        doc_ids = None
        partner_ids = self.env['res.partner'].search([('user_id', '=', self.env.user.id), ('is_doctor', '=', True)])
        if partner_ids:
            doc_ids = self.env['medical.physician'].search([('res_partner_physician_id', 'in', partner_ids.ids)])
        return doc_ids

    name = fields.Many2one('medical.patient', 'Patient ID', default=False)
    evaluation_date = fields.Many2one('medical.appointment', 'Appointment Date',
                                      help="Enter or select the date / ID of the appointment related to this evaluation")
    evaluation_start = fields.Datetime('Start of Evaluation', required=True, default=fields.Datetime.now)
    evaluation_endtime = fields.Datetime('End of Evaluation', required=True)
    next_evaluation = fields.Many2one('medical.appointment', 'Next Appointment')
    user_id = fields.Many2one('res.users', 'Last Changed by', readonly=True, default=lambda self: self.env.user)
    doctor = fields.Many2one('medical.physician', 'Doctor', readonly=True, default=_get_default_doctor)
    speciality = fields.Many2one('medical.speciality', 'Specialty', )
    information_source = fields.Char('Source', size=128, default='Self',
                                     help='Source of Information, eg : Self, relative, friend ...')
    reliable_info = fields.Boolean('Reliable', default=True,
                                   help="Uncheck this option if the information provided by the source seems not reliable")
    derived_from = fields.Many2one('medical.physician', 'Derived from Doctor', readonly=True, help="Physician who escalated / derived the case")
    derived_to = fields.Many2one('medical.physician', 'Derived to Doctor', help="Physician to whom escalate / derive the case")
    evaluation_type = fields.Selection([
        ('a', 'Ambulatory'),
        ('e', 'Emergency'),
        ('i', 'Inpatient'),
        ('pa', 'Pre-arraganged appointment'),
        ('pc', 'Periodic control'),
        ('p', 'Phone call'),
        ('t', 'Telemedicine')], 'Evaluation Type', default='pa')
    chief_complaint = fields.Char('Chief Complaint', size=128, help='Chief Complaint')
    present_illness = fields.Text('Present Illness')
    evaluation_summary = fields.Text('Evaluation Summary')
    urgency = fields.Selection([
        ('a', 'Normal'),
        ('b', 'Urgent'),
        ('c', 'Medical Emergency')], 'Urgency', sort=False)
    visit_type = fields.Selection([
        ('new', 'New health condition'),
        ('followup', 'Followup'),
        ('chronic', 'Chronic condition checkup'),
        ('well_child', 'Well Child visit'),
        ('well_woman', 'Well Woman visit'),
        ('well_man', 'Well Man visit')], 'Visit', sort=False)
    hip = fields.Float('Hip', help="Hip circumference in centimeters, eg 100'")
    whr = fields.Float('WHR', help="Waist to hip ratio")
    glycemia = fields.Float('Glycemia', help="Last blood glucose level. Can be approximative.")
    hba1c = fields.Float('Glycated Hemoglobin', help="Last Glycated Hb level. Can be approximative.")
    cholesterol_total = fields.Integer('Last Cholesterol', help="Last cholesterol reading. Can be approximative")
    hdl = fields.Integer('Last HDL', help="Last HDL Cholesterol reading. Can be approximative")
    ldl = fields.Integer('Last LDL', help="Last LDL Cholesterol reading. Can be approximative")
    tag = fields.Integer('Last TAGs', help="Triacylglycerols (triglicerides) level. Can be approximative")
    systolic = fields.Integer('Systolic Pressure')
    diastolic = fields.Integer('Diastolic Pressure')
    bpm = fields.Integer('Heart Rate', help="Heart rate expressed in beats per minute")
    respiratory_rate = fields.Integer('Respiratory Rate', help="Respiratory rate expressed in breaths per minute")
    osat = fields.Integer('Oxygen Saturation', help="Oxygen Saturation (arterial).")
    malnutrition = fields.Boolean('Malnutrition',
                                  help="Check this box if the patient show signs of malnutrition. If not associated to a disease, please encode the correspondent disease on the patient disease history. For example, Moderate protein-energy malnutrition, E44.0 in ICD-10 encoding")
    dehydration = fields.Boolean('Dehydration',
                                 help="Check this box if the patient show signs of dehydration. If not associated to a disease, please encode the correspondent disease on the patient disease history. For example, Volume Depletion, E86 in ICD-10 encoding")
    temperature = fields.Float('Temperature (celsius)')
    weight = fields.Float('Weight (kg)')
    height = fields.Float('Height (cm)')
    bmi = fields.Float('Body Mass Index')
    head_circumference = fields.Float('Head Circumference', help="Head circumference")
    abdominal_circ = fields.Float('Abdominal Circumference')
    loc_eyes = fields.Selection([
        ('1', 'Does not Open Eyes'),
        ('2', 'Opens eyes in response to painful stimuli'),
        ('3', 'Opens eyes in response to voice'),
        ('4', 'Opens eyes spontaneously')], 'Glasgow - Eyes', default='4', sort=False)
    loc_verbal = fields.Selection([
        ('1', 'Makes no sounds'),
        ('2', 'Incomprehensible sounds'),
        ('3', 'Utters inappropriate words'),
        ('4', 'Confused, disoriented'),
        ('5', 'Oriented, converses normally')], 'Glasgow - Verbal', default='5', sort=False)
    loc_motor = fields.Selection([
        ('1', 'Makes no movement'),
        ('2', 'Extension to painful stimuli - decerebrate response -'),
        ('3', 'Abnormal flexion to painful stimuli (decorticate response)'),
        ('4', 'Flexion / Withdrawal to painful stimuli'),
        ('5', 'Localizes painful stimuli'),
        ('6', 'Obeys commands')], 'Glasgow - Motor', default='6', sort=False)
    loc = fields.Integer('Level of Consciousness',
                         help="Level of Consciousness - on Glasgow Coma Scale :  1=coma - 15=normal")
    violent = fields.Boolean('Violent Behaviour',
                             help="Check this box if the patient is agressive or violent at the moment")
    mood = fields.Selection([
        ('n', 'Normal'),
        ('s', 'Sad'),
        ('f', 'Fear'),
        ('r', 'Rage'),
        ('h', 'Happy'),
        ('d', 'Disgust'),
        ('e', 'Euphoria'),
        ('fl', 'Flat')], 'Mood')
    orientation = fields.Boolean('Orientation', help="Check this box if the patient is disoriented in time and/or space")
    memory = fields.Boolean('Memory', help="Check this box if the patient has problems in short or long term memory")
    knowledge_current_events = fields.Boolean('Knowledge of Current Events', help="Check this box if the patient can not respond to public notorious events")
    judgment = fields.Boolean('Jugdment', help="Check this box if the patient can not interpret basic scenario solutions")
    abstraction = fields.Boolean('Abstraction', help="Check this box if the patient presents abnormalities in abstract reasoning")
    vocabulary = fields.Boolean('Vocabulary', help="Check this box if the patient lacks basic intelectual capacity, when she/he can not describe elementary objects")
    calculation_ability = fields.Boolean('Calculation Ability', help="Check this box if the patient can not do simple arithmetic problems")
    object_recognition = fields.Boolean('Object Recognition', help="Check this box if the patient suffers from any sort of gnosia disorders, such as agnosia, prosopagnosia ...")
    praxis = fields.Boolean('Praxis', help="Check this box if the patient is unable to make voluntary movements")
    diagnosis = fields.Many2one('medical.pathology', 'Presumptive Diagnosis', help="Presumptive Diagnosis")
    info_diagnosis = fields.Text('Presumptive Diagnosis: Extra Info')
    directions = fields.Text('Plan')
    actions = fields.One2many('medical.directions', 'name', 'Actions')
    secondary_conditions = fields.One2many('medical.secondary_condition', 'name', 'Secondary Conditions', help='Other, Secondary conditions found on the patient')
    diagnostic_hypothesis = fields.One2many('medical.diagnostic_hypothesis', 'name', 'Hypotheses / DDx', help='Other Diagnostic Hypotheses / Differential Diagnosis (DDx)')
    signs_and_symptoms = fields.One2many('medical.signs_and_symptoms', 'name', 'Signs and Symptoms', help='Enter the Signs and Symptoms for the patient in this evaluation.')

    #         'loc_eyes' : fields.integer('Level of Consciousness - Eyes', help="Eyes Response - Glasgow Coma Scale - 1 to 4"),
    #         'loc_verbal' : fields.integer('Level of Consciousness - Verbal', help="Verbal Response - Glasgow Coma Scale - 1 to 5"),
    #         'loc_motor' : fields.integer('Level of Consciousness - Motor', help="Motor Response - Glasgow Coma Scale - 1 to 6"),
    #         'edema' : fields.boolean ('Edema', help="Please also encode the correspondent disease on the patient disease history. For example,  R60.1 in ICD-10 encoding"),
    #         'petechiae' : fields.boolean ('Petechiae'),
    #         'hematoma' : fields.boolean ('Hematomas'),
    #         'cyanosis' : fields.boolean ('Cyanosis', help="If not associated to a disease, please encode it on the patient disease history. For example,  R23.0 in ICD-10 encoding"),
    #         'acropachy' : fields.boolean ('Acropachy', help="Check if the patient shows acropachy / clubbing"),
    #         'nystagmus' : fields.boolean ('Nystagmus', help="If not associated to a disease, please encode it on the patient disease history. For example,  H55 in ICD-10 encoding"),
    #         'miosis' : fields.boolean ('Miosis', help="If not associated to a disease, please encode it on the patient disease history. For example,  H57.0 in ICD-10 encoding" ),
    #         'mydriasis' : fields.boolean ('Mydriasis', help="If not associated to a disease, please encode it on the patient disease history. For example,  H57.0 in ICD-10 encoding"),
    #         'cough' : fields.boolean ('Cough', help="If not associated to a disease, please encode it on the patient disease history."),
    #         'palpebral_ptosis' : fields.boolean ('Palpebral Ptosis', help="If not associated to a disease, please encode it on the patient disease history"),
    #         'arritmia' : fields.boolean ('Arritmias', help="If not associated to a disease, please encode it on the patient disease history"),
    #         'heart_murmurs' : fields.boolean ('Heart Murmurs'),
    #         'heart_extra_sounds' : fields.boolean ('Heart Extra Sounds', help="If not associated to a disease, please encode it on the patient disease history"),
    #         'jugular_engorgement' : fields.boolean ('Tremor', help="If not associated to a disease, please encode it on the patient disease history"),
    #         'ascites' : fields.boolean ('Ascites', help="If not associated to a disease, please encode it on the patient disease history"),
    #         'lung_adventitious_sounds' : fields.boolean ('Lung Adventitious sounds', help="Crackles, wheezes, ronchus.."),
    #         'bronchophony' : fields.boolean ('Bronchophony'),
    #         'increased_fremitus' : fields.boolean ('Increased Fremitus'),
    #         'decreased_fremitus' : fields.boolean ('Decreased Fremitus'),
    #         'jaundice' : fields.boolean ('Jaundice', help="If not associated to a disease, please encode it on the patient disease history"),
    #         'lynphadenitis' : fields.boolean ('Linphadenitis', help="If not associated to a disease, please encode it on the patient disease history"),
    #         'breast_lump' : fields.boolean ('Breast Lumps'),
    #         'breast_asymmetry' : fields.boolean ('Breast Asymmetry'),
    #         'nipple_inversion' : fields.boolean ('Nipple Inversion'),
    #         'nipple_discharge' : fields.boolean ('Nipple Discharge'),
    #         'peau_dorange' : fields.boolean ('Peau d orange',help="Check if the patient has prominent pores in the skin of the breast" ),
    #         'gynecomastia' : fields.boolean ('Gynecomastia'),
    #         'masses' : fields.boolean ('Masses', help="Check when there are findings of masses / tumors / lumps"),
    #         'hypotonia' : fields.boolean ('Hypotonia', help="Please also encode the correspondent disease on the patient disease history."),
    #         'hypertonia' : fields.boolean ('Hypertonia', help="Please also encode the correspondent disease on the patient disease history."),
    #         'pressure_ulcers' : fields.boolean ('Pressure Ulcers', help="Check when Decubitus / Pressure ulcers are present"),
    #         'goiter' : fields.boolean ('Goiter'),
    #         'alopecia' : fields.boolean ('Alopecia', help="Check when alopecia - including androgenic - is present"),
    #         'xerosis' : fields.boolean ('Xerosis'),
    #         'erithema' : fields.boolean ('Erithema', help="Please also encode the correspondent disease on the patient disease history."),

    #         'symptom_pain' : fields.boolean ('Pain'),
    #         'symptom_pain_intensity' : fields.integer ('Pain intensity', help="Pain intensity from 0 (no pain) to 10 (worst possible pain)"),
    #         'symptom_arthralgia' : fields.boolean ('Arthralgia'),
    #         'symptom_myalgia' : fields.boolean ('Myalgia'),
    #         'symptom_abdominal_pain' : fields.boolean ('Abdominal Pain'),
    #         'symptom_cervical_pain' : fields.boolean ('Cervical Pain'),
    #         'symptom_thoracic_pain' : fields.boolean ('Thoracic Pain'),
    #         'symptom_lumbar_pain' : fields.boolean ('Lumbar Pain'),
    #         'symptom_pelvic_pain' : fields.boolean ('Pelvic Pain'),
    #         'symptom_headache' : fields.boolean ('Headache'),
    #         'symptom_odynophagia' : fields.boolean ('Odynophagia'),
    #         'symptom_sore_throat' : fields.boolean ('Sore throat'),
    #         'symptom_otalgia' : fields.boolean ('Otalgia'),
    #         'symptom_tinnitus' : fields.boolean ('Tinnitus'),
    #         'symptom_ear_discharge' : fields.boolean ('Ear Discharge'),
    #         'symptom_hoarseness' : fields.boolean ('Hoarseness'),
    #         'symptom_chest_pain' : fields.boolean ('Chest Pain'),
    #         'symptom_chest_pain_excercise' : fields.boolean ('Chest Pain on excercise only'),
    #         'symptom_orthostatic_hypotension' : fields.boolean ('Orthostatic hypotension', help="If not associated to a disease,please encode it on the patient disease history. For example,  I95.1 in ICD-10 encoding"),
    #         'symptom_astenia' : fields.boolean ('Astenia'),
    #         'symptom_anorexia' : fields.boolean ('Anorexia'),
    #         'symptom_weight_change' : fields.boolean ('Sudden weight change'),
    #         'symptom_abdominal_distension' : fields.boolean ('Abdominal Distension'),
    #         'symptom_hemoptysis' : fields.boolean ('Hemoptysis'),
    #         'symptom_hematemesis' : fields.boolean ('Hematemesis'),
    #         'symptom_epistaxis' : fields.boolean ('Epistaxis'),
    #         'symptom_gingival_bleeding' : fields.boolean ('Gingival Bleeding'),
    #         'symptom_rinorrhea' : fields.boolean ('Rinorrhea'),
    #         'symptom_nausea' : fields.boolean ('Nausea'),
    #         'symptom_vomiting' : fields.boolean ('Vomiting'),
    #         'symptom_dysphagia' : fields.boolean ('Dysphagia'),
    #         'symptom_polydipsia' : fields.boolean ('Polydipsia'),
    #         'symptom_polyphagia' : fields.boolean ('Polyphagia'),
    #         'symptom_polyuria' : fields.boolean ('Polyuria'),
    #         'symptom_nocturia' : fields.boolean ('Nocturia'),
    #         'symptom_vesical_tenesmus' : fields.boolean ('Vesical Tenesmus'),
    #         'symptom_pollakiuria' : fields.boolean ('Pollakiuiria'),
    #         'symptom_dysuria' : fields.boolean ('Dysuria'),
    #         'symptom_stress' : fields.boolean ('Stressed-out'),
    #         'symptom_mood_swings' : fields.boolean ('Mood Swings'),
    #         'symptom_pruritus' : fields.boolean ('Pruritus'),
    #         'symptom_insomnia' : fields.boolean ('Insomnia'),
    #         'symptom_disturb_sleep' : fields.boolean ('Disturbed Sleep'),
    #         'symptom_dyspnea' : fields.boolean ('Dyspnea'),
    #         'symptom_orthopnea' : fields.boolean ('Orthopnea'),
    #         'symptom_amnesia' : fields.boolean ('Amnesia'),
    #         'symptom_paresthesia' : fields.boolean ('Paresthesia'),
    #         'symptom_paralysis' : fields.boolean ('Paralysis'),
    #         'symptom_syncope' : fields.boolean ('Syncope'),
    #         'symptom_dizziness' : fields.boolean ('Dizziness'),
    #         'symptom_vertigo' : fields.boolean ('Vertigo'),
    #         'symptom_eye_glasses' : fields.boolean ('Eye glasses',help="Eye glasses or contact lenses"),
    #         'symptom_blurry_vision' : fields.boolean ('Blurry vision'),
    #         'symptom_diplopia' : fields.boolean ('Diplopia'),
    #         'symptom_photophobia' : fields.boolean ('Photophobia'),
    #         'symptom_dysmenorrhea' : fields.boolean ('Dysmenorrhea'),
    #         'symptom_amenorrhea' : fields.boolean ('Amenorrhea'),
    #         'symptom_metrorrhagia' : fields.boolean ('Metrorrhagia'),
    #         'symptom_menorrhagia' : fields.boolean ('Menorrhagia'),
    #         'symptom_vaginal_discharge' : fields.boolean ('Vaginal Discharge'),
    #         'symptom_urethral_discharge' : fields.boolean ('Urethral Discharge'),
    #         'symptom_diarrhea' : fields.boolean ('Diarrhea'),
    #         'symptom_constipation' : fields.boolean ('Constipation'),
    #         'symptom_rectal_tenesmus' : fields.boolean ('Rectal Tenesmus'),
    #         'symptom_melena' : fields.boolean ('Melena'),
    #         'symptom_proctorrhagia' : fields.boolean ('Proctorrhagia'),
    #         'symptom_xerostomia' : fields.boolean ('Xerostomia'),
    #         'symptom_sexual_dysfunction' : fields.boolean ('Sexual Dysfunction'),
    #         'notes' : fields.text ('Notes'),

    @api.depends('evaluation_start')
    def name_get(self):
        result = []
        for partner in self:
            name = partner.evaluation_start
            result.append((partner.id, name))
        return result

    @api.onchange('height', 'weight')
    def onchange_height_weight(self):
        if self.height and self.weight:
            self.bmi = self.weight / ((self.height / 100) ** 2) or 0.00

    @api.onchange('abdominal_circ', 'hip')
    def onchange_with_whr(self):
        if self.abdominal_circ > 0 and self.hip:
            self.whr = self.waist / self.hip or 0.00

    @api.onchange('loc_motor', 'loc_eyes', 'loc_verbal')
    def onchange_loc(self):
        if not self.loc_motor:
            self.loc_motor = 0
        if not self.loc_eyes:
            self.loc_eyes = 0
        if not self.loc_verbal:
            self.loc_verbal = 0
        self.loc = int(self.loc_motor) + int(self.loc_eyes) + int(self.loc_verbal)


# PATIENT DIRECTIONS (to be used also in surgeries if using standards like ICD10-PCS)
class MedicalDirections(models.Model):
    _name = "medical.directions"

    name = fields.Many2one('medical.patient.evaluation', 'Evaluation', readonly=True)
    procedure = fields.Many2one('medical.procedure', 'Procedure', required=True)
    comments = fields.Char('Comments', size=128)


# PATIENT DIRECTIONS (to be used also in surgeries if using standards like ICD10-PCS)
class MedicalSecondaryCondition(models.Model):
    _name = "medical.secondary_condition"

    name = fields.Many2one('medical.patient.evaluation', 'Evaluation', readonly=True)
    procedure = fields.Many2one('medical.pathology', 'Pathology', required=True)
    comments = fields.Char('Comments', size=128)


class medical_diagnostic_hypothesis(models.Model):
    _name = "medical.diagnostic_hypothesis"

    name = fields.Many2one('medical.patient.evaluation', 'Evaluation', readonly=True)
    procedure = fields.Many2one('medical.pathology', 'Pathology', required=True)
    comments = fields.Char('Comments', size=128)


# medical_diagnostic_hypothesis()


class MedicalSignsAndSymptoms(models.Model):
    _name = "medical.signs_and_symptoms"

    name = fields.Many2one('medical.patient.evaluation', 'Evaluation', readonly=True)
    sign_or_symptom = fields.Selection([
        ('sign', 'Sign'),
        ('symptom', 'Symptom')], 'Subjective / Objective', required=True)
    clinical = fields.Many2one('medical.pathology', 'Sign or Symptom', required=True)
    comments = fields.Char('Comments', size=128)

class AccountInvoice(models.Model):
    _inherit = 'account.move'
    _group_by = 'invoice_types'

    invoice_types = fields.Selection([
        ('prescription', 'Prescription'),
        ('appointment', 'Appointment'),
        ('lab', 'Lab'),
        ('imaging', 'Imaging'),
    ], string='Category')



# PRESCRIPTION ORDER
class MedicalPrescriptionOrder(models.Model):
    _name = "medical.prescription.order"
    _description = "prescription order"

    @api.model
    def _get_default_doctor(self):
        doc_ids = None
        partner_ids = self.env['res.partner'].search([('user_id', '=', self.env.user.id), ('is_doctor', '=', True)])
        if partner_ids:
            doc_ids = self.env['medical.physician'].search([('res_partner_physician_id', 'in', partner_ids.ids)])
        return doc_ids

    name = fields.Many2one('medical.patient', 'Patient ID', related='pid1.patient' , required=True)
    prescription_id = fields.Char('Prescription ID', default='New', help='Type in the ID of this prescription')
    prescription_date = fields.Datetime('Prescription Date', default=fields.Datetime.now)
    user_id = fields.Many2one('res.users', 'Log In User', readonly=True, default=lambda self: self.env.user)
    pharmacy = fields.Many2one('res.partner', 'Pharmacy', domain=[('is_pharmacy', '=', True)])
    prescription_line = fields.One2many('medical.prescription.line', 'name', 'Prescription line')
    notes = fields.Text('Prescription Notes')
    pid1 = fields.Many2one('medical.appointment', 'Appointment')
    doctor = fields.Many2one('medical.physician', 'Prescribing Doctor', help="Physician's Name", default=_get_default_doctor)
    p_name = fields.Char('Demo', default=False)
    confirmed = fields.Boolean(string="Confirmed", default=False)


    _sql_constraints = [
        ('pid1', 'unique (pid1)', 'Prescription must be unique per Appointment'),
        ('prescription_id', 'unique (prescription_id)', 'Prescription ID must be unique')]

    @api.onchange('name')
    def onchange_name(self):
        domain_list = []
        domain = {}
        if self.name:
            apt_ids = self.search([('name', '=', self.name.id)])
            for apt in apt_ids:
                if apt.pid1:
                    domain_list.append(apt.pid1.id)
        domain['pid1'] = [('id', 'not in', domain_list)]
        return {'domain': domain}

    @api.model
    def create(self, vals):
        if vals.get('prescription_id', 'New') == 'New':
            vals['prescription_id'] = self.env['ir.sequence'].next_by_code('medical.prescription') or 'New'
        result = super(MedicalPrescriptionOrder, self).create(vals)
        return result

        # def onchange_p_name(self, cr, uid, ids, p_name,context = None ):
        #  n_name=context.get('name')
        #  d_name=context.get('physician_id')
        #  v={}
        #  v['name'] =  n_name
        #  v['doctor'] =  d_name
        #  return {'value': v}


    # def get_date(self, cr, uid, ids, date1,lang):
    #     new_date=''
    #     if date1:
    #         search_id = self.pool.get('res.lang').search(cr,uid,[('code','=',lang)])
    #         record=self.pool.get('res.lang').browse(cr,uid,search_id)
    #         new_date=datetime.strftime(datetime.strptime(date1,'%Y-%m-%d %H:%M:%S').date(),record.date_format)
    #     return new_date

# PRESCRIPTION LINE
class MedicalPrescriptionLine(models.Model):
    _name = "medical.prescription.line"
    _description = "Basic prescription object"
    _inherits = {'medical.medication.template': 'template'}

    template = fields.Many2one('medical.medication.template', 'Template ID', required=True, index=True, ondelete="cascade")
    name = fields.Many2one('medical.prescription.order', 'Prescription ID')
    review = fields.Datetime('Review')
    quantity = fields.Integer('Quantity', default=1)
    refills = fields.Integer('Refills')
    allow_substitution = fields.Boolean('Allow substitution')
    short_comment = fields.Char('Comment', size=128, help='Short comment on the specific drug')
    prnt = fields.Boolean('Print', default=True, help='Check this box to print this line of the prescription.')


# PATIENT VACCINATION INFORMATION

class MedicalVaccination(models.Model):

    @api.constrains('vaccine_expiration_date')
    def _check_vaccine_expiration_date(self):
        for obj in self:
            if obj.vaccine_expiration_date < obj.date:
                raise ValidationError(_("EXPIRED VACCINE. PLEASE INFORM THE LOCAL HEALTH AUTHORITIES AND DO NOT USE IT !!"))

    @api.onchange('date', 'vaccine_expiration_date')
    def onchange_vaccination_expiration_date(self):
        if self.vaccine_expiration_date and self.date and self.vaccine_expiration_date < self.date:
            self.vaccine_expiration_date = False
            warning = {
                'title': _('EXPIRED VACCINE !'),
                'message': _('Please Dispose it!'),
            }
            return {'warning': warning}

    _name = "medical.vaccination"

    name = fields.Many2one('medical.patient', 'Patient ID', readonly=True)
    vaccine = fields.Many2one('product.product', 'Name', domain=[('is_vaccine', '=', "1")],
                              help="Vaccine Name. Make sure that the vaccine (product) has all the proper information at product level. Information such as provider, supplier code, tracking number, etc.. This information must always be present. If available, please copy / scan the vaccine leaflet and attach it to this record")
    vaccine_expiration_date = fields.Datetime('Expiration date')
    vaccine_lot = fields.Char('Lot Number', size=128,
                              help="Please check on the vaccine (product) production lot number and tracking number when available !")
    institution = fields.Many2one('res.partner', 'Institution', domain=[('is_institution', '=', "1")],
                                  help="Medical Center where the patient is being or was vaccinated")
    date = fields.Datetime('Date', default=fields.Datetime.now)
    next_dose_date = fields.Datetime('Next Dose')
    dose = fields.Integer('Dose Number', default=1)
    observations = fields.Char('Observations', size=128)

    _sql_constraints = [
        ('dose_unique', 'unique (name,dose,vaccine)', 'This vaccine dose has been given already to the patient '),
        ('next_dose_date_check', "CHECK (date < next_dose_date)",
         "The Vaccine first dose date must be before Vaccine next dose Date !")]


# HEALTH CENTER / HOSPITAL INFRASTRUCTURE
class MedicalHospitalBuilding(models.Model):
    _name = "medical.hospital.building"

    name = fields.Char('Name', size=128, required=True, help="Name of the building within the institution")
    institution = fields.Many2one('res.partner', 'Institution', domain=[('is_institution', '=', "1")], help="Medical Center")
    code = fields.Char('Code', size=64)
    extra_info = fields.Text('Extra Info')


class MedicalHospitalUnit(models.Model):
    _name = "medical.hospital.unit"

    name = fields.Char('Name', size=128, required=True, help="Name of the unit, eg Neonatal, Intensive Care, ...")
    institution = fields.Many2one('res.partner', 'Institution', domain=[('is_institution', '=', "1")], help="Medical Center")
    code = fields.Char('Code', size=64)
    extra_info = fields.Text('Extra Info')


class MedicalHospitalWard(models.Model):
    _name = "medical.hospital.ward"

    name = fields.Char('Name', required=True, size=128, help="Ward / Room code")
    institution = fields.Many2one('res.partner', 'Institution', domain=[('is_institution', '=', "1")], help="Medical Center")
    building = fields.Many2one('medical.hospital.building', 'Building')
    floor = fields.Integer('Floor Number')
    unit = fields.Many2one('medical.hospital.unit', 'Unit')
    private = fields.Boolean('Private', help="Check this option for private room")
    bio_hazard = fields.Boolean('Bio Hazard', help="Check this option if there is biological hazard")
    number_of_beds = fields.Integer('Number of beds', help="Number of patients per ward", default=1)
    telephone = fields.Boolean('Telephone access')
    ac = fields.Boolean('Air Conditioning')
    private_bathroom = fields.Boolean('Private Bathroom')
    guest_sofa = fields.Boolean('Guest sofa-bed')
    tv = fields.Boolean('Television')
    internet = fields.Boolean('Internet Access')
    refrigerator = fields.Boolean('Refrigetator')
    microwave = fields.Boolean('Microwave')
    gender = fields.Selection([
        ('men', 'Men Ward'),
        ('women', 'Women Ward'),
        ('unisex', 'Unisex')], 'Gender', required=True, default='unisex')
    state = fields.Selection([
        ('beds_available', 'Beds available'),
        ('full', 'Full'),
        ('na', 'Not available')], 'Status')
    extra_info = fields.Text('Extra Info')


class MedicalHospitalBed(models.Model):
    _name = "medical.hospital.bed"
    _rec_name = 'name'

    name = fields.Char(related="product_medical_hospital_bed_id.name")
    product_medical_hospital_bed_id = fields.Many2one('product.product', 'Bed', domain=[('is_bed', '=', "1")], help="Bed Number")
    ward = fields.Many2one('medical.hospital.ward', 'Ward', help="Ward or room")
    bed_type = fields.Selection([
        ('gatch', 'Gatch Bed'),
        ('electric', 'Electric'),
        ('stretcher', 'Stretcher'),
        ('low', 'Low Bed'),
        ('low_air_loss', 'Low Air Loss'),
        ('circo_electric', 'Circo Electric'),
        ('clinitron', 'Clinitron')], 'Bed Type', required=True, default='gatch')
    telephone_number = fields.Char('Telephone Number', size=128, help="Telephone number / Extension")
    extra_info = fields.Text('Extra Info')
    state = fields.Selection([
        ('free', 'Free'),
        ('reserved', 'Reserved'),
        ('occupied', 'Occupied'),
        ('na', 'Not available')], 'Status', readonly=True, default='free')

    @api.model
    def name_create(self, name):
        bed_id = self.create({'name': self.name})
        return [(self.bed_id)]


class MedicalHospitalOpratingRoom(models.Model):
    _name = "medical.hospital.oprating.room"

    name = fields.Char('Name', size=128, required=True, help='Name of the Operating Room')
    institution = fields.Many2one('res.partner', 'Institution', domain=[('is_institution', '=', True)], help='Medical Center')
    building = fields.Many2one('medical.hospital.building', 'Building', index=True)
    unit = fields.Many2one('medical.hospital.unit', 'Unit')
    extra_info = fields.Text('Extra Info')

    _sql_constraints = [
        ('name_uniq', 'unique (name, institution)', 'The Operating Room code must be unique per Health Center.')]


class DoctorSlot(models.Model):
    _name = 'doctor.slot'
    _description = 'Doctor Slot'

    doctor_id = fields.Many2one('medical.physician', string='Doctor')
    weekday = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday')], string='Week Day', required=True)
    start_hour = fields.Float('Starting Hour')
    end_hour = fields.Float('Ending Hour')

    @api.model
    def get_doctors_slot(self, target_date=False, doctor=False):
        if target_date:
            ask_time = datetime.strptime(target_date, "%a %b %d %Y %H:%M:%S %Z%z").date()
            weekday = ask_time.isoweekday()
        else:
            weekday = datetime.today().isoweekday()

        domain = [('weekday', '=', str(weekday))]
        if doctor:
            domain += [('doctor_id', '=', int(doctor))]
        slot_ids = sorted(self.search(domain), reverse=True)
        data_dict = {}
        for lt in slot_ids:
            doctor_id = lt.doctor_id
            start_hour = '{0:02.0f}:{1:02.0f}'.format(*divmod(lt.start_hour * 60, 60))
            end_hour = '{0:02.0f}:{1:02.0f}'.format(*divmod(lt.end_hour * 60, 60))
            if doctor_id.id not in data_dict:
                data_dict[doctor_id.id] = {
                    'id': doctor_id.id,
                    'name': doctor_id.res_partner_medical_physician_id.name,
                    'count': 1,
                    'time_slots': [{'start_hour': start_hour, 'end_hour': end_hour}]
                }
            else:
                data_dict[doctor_id.id]['count'] += 1
                data_dict[doctor_id.id]['time_slots'].append({'start_hour': start_hour, 'end_hour': end_hour})

        final_list = []
        for i in data_dict:
            final_list.append(data_dict.get(i))
        return final_list

    @api.model
    def get_doctors_slot_validation(self, target_date=False, doctor=False):
        is_available_slot = False
        if target_date:
            ask_time = datetime.strptime(target_date, "%a %b %d %Y %H:%M:%S %Z%z").date()
            weekday = ask_time.isoweekday()
        else:
            weekday = datetime.today().isoweekday()
        domain = [('weekday', '=', str(weekday))]
        if doctor:
            domain += [('doctor_id', '=', int(doctor))]
        slot_ids = sorted(self.search(domain), reverse=True)
        for lt in slot_ids:
            start_hour = '{0:02.0f}:{1:02.0f}'.format(*divmod(lt.start_hour * 60, 60))
            end_hour = '{0:02.0f}:{1:02.0f}'.format(*divmod(lt.end_hour * 60, 60))
            ask_time = datetime.strptime(target_date, "%a %b %d %Y %H:%M:%S %Z%z").date()

            start_time = datetime.strptime(start_hour, '%H:%M').time()
            start_date_time = datetime.combine(ask_time, start_time)

            end_time = datetime.strptime(end_hour, '%H:%M').time()
            end_date_time = datetime.combine(ask_time, end_time)

            if self.env.context.get('dateToString') and self.env.context.get('from_time'):
                str_date = datetime.strptime(self.env.context.get('dateToString'), "%a %b %d %Y %H:%M:%S %Z%z").date()
                str_date = str(str_date) + ' ' + self.env.context.get('from_time')
                datetime_object = datetime.strptime(str_date, '%Y-%m-%d %H:%M:%S')
                if datetime_object >= start_date_time and datetime_object <= end_date_time:
                    is_available_slot = True
        return is_available_slot
