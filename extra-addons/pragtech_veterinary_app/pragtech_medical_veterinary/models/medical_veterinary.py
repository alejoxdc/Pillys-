from odoo import api, fields, models, tools, _
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, RedirectWarning, ValidationError
import logging

_logger = logging.getLogger(__name__)


class pet_breed(models.Model):
    _name = "pet.breed"

    name = fields.Char('Name', size=128, required=True)
    code = fields.Char('Code', size=128)

    _sql_constraints = [
        ('code_uniq', 'unique (name)', 'Name must be unique')]


class pet_type(models.Model):
    _name = "pet.type"

    name = fields.Char('Name', size=128, required=True)
    code = fields.Char('Code', size=128)

    _sql_constraints = [
        ('code_uniq', 'unique (name)', 'Name must be unique')]


class pet_blood_group(models.Model):
    _name = "pet.blood.group"
    _description = "Blood Group"

    name = fields.Char('Name', size=128, required=True)
    code = fields.Char('Code', size=128)

    _sql_constraints = [
        ('code_uniq', 'unique (name)', 'Name must be unique')]


class partner_patient(models.Model):
    #    _name = "res.partner"
    _inherit = "res.partner"

    is_pet = fields.Boolean('Pet', help="Check if the partner is a pet.", default=False)
    is_owner = fields.Boolean('Owner', help="Check if the partner is a owner of pet", default=False)
    owner_name = fields.Many2one('res.partner', 'Owner Name', )


#         'code' : fields.Char ('Code', size=128)
#         'code' : fields.Char ('Code', size=128)
#         'code' : fields.Char ('Code', size=128)


#     def default_get(self, cr, uid, fields, context=None):
#          if context is None: context = {}
#          res = {}
#
#          if context.has_key('is_owner'):
#               move_ids = context.get ('is_owner')
#               res.update(is_owner=move_ids)
#               res['is_patient']=False
#               res['is_pet']=False
#               res['is_person']=True
#               res['active']=True
#
#          else:
#              res['is_patient']=True
#              res['is_person']=True
#              res['is_pet']=True
#              res['active']=True
#          return res


class patient_data(models.Model):
    _inherit = "medical.patient"

    partner_id = fields.Many2one('res.partner', 'Patient', required="1",
                                 domain=[('is_patient', '=', True), ('is_person', '=', True), ('is_pet', '=', True)],
                                 help="Patient Name")
    height = fields.Float('Height')
    weight = fields.Float('Width')
    color = fields.Char('Color', size=128)
    breed_id = fields.Many2one('pet.breed', 'Breed', )
    pet_type_id = fields.Many2one('pet.type', 'Type Of Pet')
    works = fields.Boolean('Works', help="Check if the patient works at his / her house")

    @api.onchange('partner_id')
    def onchange_partnerid(self):
        v = {}
        if self.partner_id:
            return {'value': v, 'domain': {'current_address': [('id', 'in', [self.partner_id.owner_name.id])]}, }


class appointment(models.Model):

    def _check_unique_insesitive(self):

        if self.patient.name.owner_name.name != self.owner_name.name:
            return False
        return True

    _name = "medical.appointment"
    _inherit = "medical.appointment"

    owner_name = fields.Many2one('res.partner', 'Owner Name', required=True)

    _constraints = [(_check_unique_insesitive, 'Please select correct owner', ['owner_name'])]

    @api.onchange('patient', 'patient_status')
    def onchange_patient(self):

        v = {}
        my_data = {}
        if self.patient_status == 'inpatient':
            reg_pat = self.env['medical.inpatient.registration'].search([('patient.id', '=', self.patient)])[0]
            v['inpatient_registration_code'] = reg_pat.id
        else:
            v['inpatient_registration_code'] = ""
            my_data['name'] = False
            v['pres_id1'] = False
        reg_pat1 = self.patient
        v['owner_name'] = reg_pat1.partner_id.owner_name.id
        return {'value': v}

    def create_invoice(self):
        invoice_obj = self.env['account.move']
        appointment_obj = self.env['medical.appointment']
        flag1 = False
        apps = self
        pats = []
        context = dict(self._context or {})
        flag1 = self.patient.partner_id.is_pet
        pats.append(self.patient.partner_id.id)
        if pats.count(pats[0]) == len(pats):
            invoice_data = {}
            for app_id in apps:

                # Check if the appointment is invoice exempt, and stop the invoicing process
                if self.state == "draft":
                    raise UserError(_('The appointment is in Draft State. First Confirm it.'))
                if self.no_invoice:
                    raise UserError(_('The appointment is invoice exempt'))

                if self.validity_status == 'invoiced':
                    if len(apps) > 1:
                        raise UserError(_('Appointments is already invoiced'))
                    else:
                        raise UserError(_('Appointment is already invoiced'))
            #                 if self.validity_status=='no':
            #                     if len(apps) > 1:
            #                         raise  osv.except_osv(_('UserError'),_('At least one of the selected appointments can not be invoiced'))
            #                     else:
            #                         raise  osv.except_osv(_('UserError'),_('You can not invoice this appointment'))

            if flag1 == True and self.patient.partner_id.id:
                invoice_data['partner_id'] = self.patient.partner_id.owner_name.id
                invoice_data['invoice_types'] = 'appointment'
                res = self.patient.partner_id.address_get(['contact', 'invoice'])
                # invoice_data['address_contact_id'] = res['contact']
                # invoice_data['address_invoice_id'] = res['invoice']
                # invoice_data['account_id'] = self.patient.partner_id.property_account_receivable_id.id
                invoice_data[
                    'fiscal_position_id'] = self.patient.partner_id.property_account_position_id and self.patient.partner_id.property_account_position_id.id or False
                invoice_data[
                    'invoice_payment_term_id'] = self.patient.partner_id.property_payment_term_id and self.patient.partner_id.property_payment_term_id.id or False
                invoice_data['move_type'] = 'out_invoice'

            elif flag1 == False and self.patient.partner_id.id:
                invoice_data['partner_id'] = self.patient.partner_id.id
                # res = self.pool.get('res.partner').address_get([self.patient.partner_id.id], ['contact', 'invoice'])
                # invoice_data['address_contact_id'] = res['contact']
                # invoice_data['address_invoice_id'] = res['invoice']
                # invoice_data['account_id'] = self.patient.partner_id.property_account_receivable_id.id
                invoice_data[
                    'fiscal_position_id'] = self.patient.partner_id.property_account_position_id and self.patient.partner_id.property_account_position_id.id or False
                invoice_data[
                    'invoice_payment_term_id'] = self.patient.partner_id.property_payment_term_id and self.patient.partner_id.property_payment_term_id.id or False
                invoice_data['move_type'] = 'out_invoice'
            prods_data = {}
            for app_id in apps:
                #                 appointment = appointment_obj.browse( cr, uid, app_id)
                logging.debug('appointment = %s; self.consultations = %s', appointment, self.consultations)
                if self.consultations:
                    logging.debug('self.consultations = %s; self.consultations.id = %s', self.consultations,
                                  self.consultations.id)
                    #                     if prods_data.has_key(self.consultations.id):
                    if self.consultations.id in prods_data:
                        prods_data[self.consultations.id]['quantity'] += 1
                    else:
                        a = self.consultations.product_tmpl_id.property_account_income_id.id
                        if not a:
                            a = self.consultations.categ_id.property_account_income_categ_id.id
                        prods_data[self.consultations.id] = {'product_id': self.consultations.id,
                                                             'name': self.consultations.name,
                                                             'quantity': 1,
                                                             'account_id': a,
                                                             'price_unit': self.consultations.lst_price}
                else:
                    raise UserError(_('No consultation service is connected with the selected appointments'))

            product_lines = []
            #             for prod_id, prod_data in prods_data.items():
            for prod_id, prod_data in list(prods_data.items()):
                product_lines.append((0, None, {'product_id': prod_data['product_id'],
                                                'name': prod_data['name'],
                                                'quantity': prod_data['quantity'],
                                                'account_id': prod_data['account_id'],
                                                'price_unit': prod_data['price_unit']}))

            invoice_data['invoice_line_ids'] = product_lines
            invoice_id = invoice_obj.create(invoice_data)
            view_id = self.env['ir.ui.view'].search([('name', '=', 'account.move.form')])
            apps.write({'inv_id': invoice_id.id, 'validity_status': 'invoiced'})
            return {
                'name': 'Create invoice',
                'view_id': view_id[0].id,
                'view_mode': 'form',
                'res_id': invoice_id.id,
                'res_model': 'account.move',
                'context': context,
                'type': 'ir.actions.act_window'
            }

        else:
            raise UserError(_('When multiple appointments are selected, patient must be the same'))


#     def onchange_patient(self, cr, uid, ids, patient,patient_status,context = None ):
#
#         v={}
#         if patient_status == 'inpatient':
#           reg_pat =self.pool.get('medical.inpatient.registration').search(cr, uid, [('patient.id','=',patient)])[0]
#           reg_pat1 =self.pool.get('medical.inpatient.registration').browse(cr,uid,reg_pat)
#           v['inpatient_registration_code'] = reg_pat1.id
#         else:
#             v['inpatient_registration_code'] = ""
#         reg_pat1 =self.pool.get('medical.patient').browse(cr,uid,patient)
#         v['owner_name'] = reg_pat1.name.owner_name.id
#         my_data = {}
#         if patient == False:
#             patient = 1
#             my_data['name'] = ''
#         else:
#             patient_data = self.pool.get('medical.patient').browse(cr,uid,patient)
#             patient_details = self.pool.get('res.partner').browse(cr,uid,patient_data.name.id)
#             my_data['name'] = patient_details.name
#         v['pres_id1'] = my_data
#         return {'value': v}

class medical_patient_lab_test(models.Model):

    def _check_unique_insesitive(self):
        reg_pat1 = self
        if reg_pat1[0].patient_id.name.owner_name.name != reg_pat1[0].owner_name.name:
            return False
        return True

    _name = "medical.patient.lab.test"
    _inherit = "medical.patient.lab.test"

    owner_name = fields.Many2one('res.partner', 'Owner Name', required=True)

    _constraints = [(_check_unique_insesitive, 'Please select correct owner', ['owner_name'])]

    @api.onchange('patient_id')
    def onchange_patient(self):
        v = {}
        reg_pat1 = self.patient_id
        v['owner_name'] = reg_pat1.partner_id.owner_name.id
        return {'value': v}


class patient_prescription_order(models.Model):

    def _check_unique_insesitive(self):

        if self.name.partner_id.owner_name.name != self.owner_name.name:
            return False
        return True

    _name = "medical.prescription.order"
    _inherit = "medical.prescription.order"

    owner_name = fields.Many2one('res.partner', string='Owner Name', related='pid1.owner_name')

    _constraints = [(_check_unique_insesitive, 'Please select correct owner', ['owner_name'])]

    def action_confirm(self):
        self.confirmed = True
        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.owner_name.id,
            'origin': self.prescription_id,
        })
        for prescription_line in self.prescription_line:
            sale_order_line = self.env['sale.order.line'].sudo().create({
                'product_id': prescription_line.medicament.product_medicament_id.id,
                'name': prescription_line.medicament.name,
                'price_unit': prescription_line.medicament.price,
                'product_uom_qty': prescription_line.quantity,
                'order_id': sale_order.id,

            })
        sale_order.action_confirm()
        stock = self.env['stock.picking'].sudo().search([('origin', '=', sale_order.name)])
        for picking in stock:
            picking.action_assign()
            picking.action_set_quantities_to_reservation()
            picking.action_confirm()
            picking.button_validate()

        notif_message = 'Medicines Dispatched Successfully'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'title': notif_message,
                # 'message': notif_message,
                'next': {
                    'type': 'ir.actions.act_window_close'
                },
            }
        }
    @api.onchange('prescription_line', 'prescription_line.quantity')
    def _check_prescription_product_qty(self):
        for record in self.prescription_line:
            if record.quantity > record.medicament.qty_available:
                raise ValidationError(
                    _("The quantity of %s Product is not available.") % record.medicament.product_medicament_id.name)
    @api.onchange('pid1')
    def onchange_appointment_patient(self):
        if self.pid1:
            for rec in self:
                rec.doctor = rec.pid1.doctor.id

    @api.onchange('partner_id')
    def onchange_name(self):
        l1 = []

        v = {}
        reg_pat1 = self.name
        v['owner_name'] = reg_pat1.partner_id.owner_name.id
        prid = self.search([])
        for p in prid:
            l1.append(p.pid1.id)
        return {'value': v, 'domain': {'pid1': [('id', 'not in', l1)]}, }


class family_code(models.Model):
    _name = "medical.family_code"
    _inherit = "medical.family_code"

    members_ids = fields.Many2many('res.partner', 'family_members_rel', 'family_id', 'members_id', 'Members',
                                   domain=[('is_pet', '=', True)])

    @api.onchange('res_partner_family_medical_id')
    def onchange_owner(self):
        reg_pat, reg_pat1 = [], []
        if self.res_partner_family_medical_id:
            reg_pat = self.env['res.partner'].search([('owner_name', '=', self.res_partner_family_medical_id.name)])
            for r in reg_pat:
                reg_pat1.append(r.id)
        return {'domain': {'members_ids': [('id', 'in', reg_pat1)]}}


class insurance(models.Model):
    _name = "medical.insurance"
    _inherit = "medical.insurance"
