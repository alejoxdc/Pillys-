# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, RedirectWarning, ValidationError

# class MedicalPatient(models.Model):
#     _name = "medical.patient"
#     _inherit = "medical.patient"
# 
#     receivable = fields.Float(related='name.credit','Receivable',help='Total amount this patient owes you',readonly=True,store=True)
    
# Add Invoicing information to the Appointment


class MedicalAppointment (models.Model):
    _name = "medical.appointment"
    _inherit = "medical.appointment"

    no_invoice = fields.Boolean('Invoice exempt', default=True)
    validity_status = fields.Selection([
        ('invoiced', 'Invoiced'),
        ('tobe', 'To be Invoiced')], 'Status', default='tobe', copy=False)
    consultations = fields.Many2one('product.product', 'Consultation Service', domain=[('type', '=', "service")], help="Consultation Services")
    inv_id = fields.Many2one('account.move', 'Invoice', readonly=True)
    pres_id1 = fields.One2many('medical.prescription.order', 'pid1', 'Prescription')
    
    def view_patient_invoice(self):
        imd = self.env['ir.model.data']
        res_id = imd._xmlid_to_res_id('account.view_move_form')
        result = {
            'name': 'Imaging Request',
            'type': 'form',
            'views': [(res_id, 'form')],
            'target': 'new',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
        }
        if self.inv_id:
            result['res_id'] = self.inv_id.id
        return result
        
    def print_prescription(self):
        self.ensure_one()
        [data] = self.read()
        if not self.pres_id1:
            raise UserError(_('No Prescription Added.'))
        # departments = self.env['hr.department'].browse(data['depts'])
        datas = {
            'ids': [],
            'model': 'medical.appointment',
            'form': data
        }
        return self.env.ref('pragtech_veterinary_app.prescription_viewreport').report_action(self, data=datas)
        
    def create_invoice(self):
        invoice_obj = self.env['account.move']
        invoice_data = {}
        prods_lines = []
        inv_id_list = []
        for appointment in self:
            if appointment.state == 'draft':
                raise UserError(_('The appointment is in Draft State. First Confirm it1.'))
            if appointment.no_invoice:
                raise UserError(_('The appointment is invoice exempt.'))
            if appointment.validity_status == 'invoiced':
                raise UserError(_('Appointments is already invoiced.'))
            if appointment.patient.partner_id.id:
                if appointment.patient.partner_id.property_account_receivable_id.id:
                    invoice_data['partner_id'] = appointment.patient.partner_id.id
                    invoice_data['fiscal_position_id'] = appointment.patient.partner_id.property_account_position_id and appointment.patient.partner_id.property_account_position_id.id or False
                    invoice_data['invoice_payment_term_id'] = appointment.patient.partner_id.property_payment_term_id and appointment.patient.partner_id.property_payment_term_id.id or False
                    invoice_data['move_type'] = 'out_invoice'
                else:
                    raise UserError(_('Account is not added for Patient.'))
            if appointment.consultations:
                    account_id = appointment.consultations.product_tmpl_id.property_account_income_id.id
                    if not account_id:
                        account_id = appointment.consultations.categ_id.property_account_income_categ_id.id
                    if not account_id:
                        raise UserError(_('Account is not added for set for Consultation.'))
                    prods_lines.append((0, None, {
                        'product_id': appointment.consultations.id,
                        'name': appointment.consultations.name,
                        'quantity': 1,
                        # 'account_id':account_id,
                        'price_unit': appointment.consultations.lst_price
                    }))
                    invoice_data['invoice_line_ids'] = prods_lines
                    invoice_id = invoice_obj.create(invoice_data)
                    inv_id_list.append(invoice_id.id)
                    appointment.write({'inv_id': invoice_id.id, 'validity_status': 'invoiced'})
                        
            else:
                raise UserError(_('No consultation service is connected with the selected appointments'))
            
        imd = self.env['ir.model.data']
        res_id = imd._xmlid_to_res_id('account.view_move_tree')
        res_id_form = imd._xmlid_to_res_id('account.view_move_form')
        result = {
            'name': 'Created invoice',
            'type': 'tree',
            'views': [(res_id, 'tree'),(res_id_form, 'form')],
            'target': 'current',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
        }
        if inv_id_list:
            result['domain'] = "[('id','in',%s)]" % inv_id_list
            result['res_id'] = inv_id_list[0]
        return result    
             
    def action_cancel(self):
        if self.validity_status == 'invoiced':
            raise ValidationError(_('Can not cancel as invoice is already created.'))
        else:
            super(MedicalAppointment, self).action_cancel()


class MedicalPatientLabTest (models.Model):
    _name = "medical.patient.lab.test"
    _inherit = "medical.patient.lab.test"
    
    no_invoice = fields.Boolean('Invoice exempt', default=True)
    validity_status = fields.Selection([
        ('invoiced', 'Invoiced'),
        ('tobe', 'To be Invoiced')], 'Status', default='tobe', copy=False)
    inv_id = fields.Many2one('account.move', 'Invoice', readonly=True)
    
    def create_lab_invoice(self):
        invoice_obj = self.env['account.move']
        invoice_data = {}
        prods_lines = []
        inv_id_list = []
        for appointment in self:
            if appointment.state == 'draft':
                raise UserError(_('The appointment is in Draft State. First Confirm it.'))
            if appointment.no_invoice:
                raise UserError(_('The appointment is invoice exempt.'))
            if appointment.validity_status == 'invoiced':
                raise UserError(_('Appointments is already invoiced.'))
            if appointment.patient_id.partner_id.id:
                if appointment.patient_id.partner_id.property_account_receivable_id.id:
                    invoice_data['partner_id'] = appointment.patient_id.partner_id.id
                    invoice_data['invoice_types'] ='lab'
                    invoice_data['fiscal_position_id'] = appointment.patient_id.partner_id.property_account_position_id and appointment.patient.partner_id.property_account_position_id.id or False
                    invoice_data['invoice_payment_term_id'] = appointment.patient_id.partner_id.property_payment_term_id and appointment.patient.partner_id.property_payment_term_id.id or False
                    invoice_data['move_type'] = 'out_invoice'
                else:
                    raise UserError(_('Account is not added for Patient.'))
            if appointment.name.product_id:
                account_id = appointment.name.product_id.product_tmpl_id.property_account_income_id.id
                if not account_id:
                    account_id = appointment.name.product_id.categ_id.property_account_income_categ_id.id
                if not account_id:
                    raise UserError(_('Account is not added for set for Consultation.'))
                prods_lines.append((0, None, {
                    'product_id': appointment.name.product_id.id,
                    'name': appointment.name.product_id.name,
                    'quantity': 1,
                    'account_id': account_id,
                    'price_unit': appointment.name.product_id.lst_price
                }))
                invoice_data['invoice_line_ids'] = prods_lines
                invoice_id = invoice_obj.create(invoice_data)
                inv_id_list.append(invoice_id.id)
                appointment.write({'inv_id': invoice_id.id, 'validity_status': 'invoiced'})
            else:
                raise UserError(_('No consultation service is connected with the selected appointments'))

        imd = self.env['ir.model.data']
        res_id = imd._xmlid_to_res_id('account.view_move_tree')
        res_id_form = imd._xmlid_to_res_id('account.view_move_form')
        
        result = {
            'name': 'Create invoice',
            'type': 'tree',
            'views': [(res_id, 'tree'), (res_id_form, 'form')],
            'target': 'current',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
        }
        if inv_id_list:
            result['domain'] = "[('id','in',%s)]" % inv_id_list
            result['res_id'] = inv_id_list[0]
        return result    
#     
#     def create_lab_invoice(self, cr, uid, ids, context={}):
# 
#         invoice_obj = self.pool.get('account.invoice')
#         test_request_obj = self.pool.get('medical.patient.lab.test')
#         
#         
#         tests = ids
#         logging.debug('tests = %s', repr(tests))
#         
#         pats = []
#         for test_id in tests:
#             #pats.append(test_request_obj.browse(cr, uid, test_id).patient_id)
#             cur_test = test_request_obj.browse(cr, uid, test_id)
#             logging.debug('cur_test = %s; pats = %s', repr(cur_test), repr(pats))
#             pats.append(cur_test.patient_id)
#         
#         logging.debug('pats = %s', repr(pats))
#         
#         if pats.count(pats[0]) == len(pats):
#             invoice_data = {}
#             for test_id in tests:
#                 #test = self.browse(cr, uid, test_id)
#                 test = test_request_obj.browse(cr, uid, test_id)
#                 logging.debug('test = %s', repr(test))
#                 if test.state == "draft":
#                     raise  osv.except_osv(_('UserError'), _('Lab test is in Draft State. First Confirm it.'))
#                 if test.invoice_status == 'invoiced':
#                     if len(tests) > 1:
#                         raise  osv.except_osv(_('UserError'), _('Lab tests is already invoiced'))
#                     else:
#                         raise  osv.except_osv(_('UserError'), _('Lab test already invoiced'))
#                 if test.invoice_status == 'no':
#                     if len(tests) > 1:
#                         raise  osv.except_osv(_('UserError'), _('Lab tests can not be invoiced'))
#                     else:
#                         raise  osv.except_osv(_('UserError'), _('You can not invoice this lab test'))
#         
#             logging.debug('test.patient_id = %s; test.patient_id.id = %s', test.patient_id, test.patient_id.id)
#             if test.patient_id.name.id:
#                 invoice_data['partner_id'] = test.patient_id.name.id
#                 res = self.pool.get('res.partner').address_get(cr, uid, [test.patient_id.name.id], ['contact', 'invoice'])
#                 invoice_data['address_contact_id'] = res['contact']
#                 invoice_data['address_invoice_id'] = res['invoice']
#                 invoice_data['account_id'] = test.patient_id.name.property_account_receivable_id.id
#                 invoice_data['fiscal_position'] = test.patient_id.name.property_account_position_id and test.patient_id.name.property_account_position_id.id or False
#                 invoice_data['payment_term'] = test.patient_id.name.property_payment_term_id and test.patient_id.name.property_payment_term_id.id or False
#         
#             prods_data = {}
#         
#             tests = [ids]
#             logging.debug('tests = %s', repr(tests))
#         
#             for test_id in tests:
#                 test = test_request_obj.browse(cr, uid, test_id)
#                 logging.debug('test.name = %s; test.name.product_id = %s; test.name.product_id.id = %s', test.name, test.name.product_id, test.name.product_id.id)
#         
#                 if prods_data.has_key(test.name.product_id.id):
#                     logging.debug('prods_data = %s; test.name.product_id.id = %s', prods_data, test.name.product_id.id)
#                     prods_data[test.name.product_id.id]['quantity'] += 1
#                 else:
#                     logging.debug('test.name.product_id.id = %s', test.name.product_id.id)
#                     a = test.name.product_id.product_tmpl_id.property_account_income_id.id
#                     if not a:
#                         a = test.name.product_id.categ_id.property_account_income_categ_id.id
#                     prods_data[test.name.product_id.id] = {'product_id':test.name.product_id.id,
#                                     'name':test.name.product_id.name,
#                                     'quantity':1,
#                                     'account_id':a,
#                                     'price_unit':test.name.product_id.lst_price}
#                     logging.debug('prods_data[test.name.product_id.id] = %s', prods_data[test.name.product_id.id])
#         
#             product_lines = []
#             for prod_id, prod_data in prods_data.items():
#                 product_lines.append((0, 0, {'product_id':prod_data['product_id'],
#                         'name':prod_data['name'],
#                         'quantity':prod_data['quantity'],
#                         'account_id':prod_data['account_id'],
#                         'price_unit':prod_data['price_unit']}))
#                 
#             invoice_data['invoice_line_ids'] = product_lines
#             invoice_id = invoice_obj.create(cr, uid, invoice_data)
#             test_request_obj.write(cr, uid, tests[0], {'invoice_status':'invoiced'})
#         
#             return {
#                 'domain': "[('id','=', " + str(invoice_id) + ")]",
#                 'name': 'Create Lab Invoice',
#                 'view_type': 'form',
#                 'view_mode': 'tree,form',
#                 'res_model': 'account.invoice',
#                 'type': 'ir.actions.act_window'
#             }
#         
#         else:
#             raise  osv.except_osv(_('UserError'), _('When multiple lab tests are selected, patient must be the same'))
# 
#     
# 
# labtest()


class PatientPrescriptionOrder (models.Model):

    _name = "medical.prescription.order"
    _inherit = "medical.prescription.order"

    no_invoice = fields.Boolean('Invoice exempt', default=True)
    invoice_status = fields.Selection([
        ('invoiced', 'Invoiced'),
        ('tobe', 'To be Invoiced')], 'Invoice Status', default='tobe')
    inv_id = fields.Many2one('account.move', 'Invoice', readonly=True)

    def create_invoice(self):
        invoice_obj = self.env['account.move']
        invoice_data = {}
        prods_lines = []
        inv_id_list = []
        for prescription in self:
            if prescription.no_invoice:
                raise UserError(_('The Prescription is invoice exempt.'))
            if prescription.invoice_status == 'invoiced':
                raise UserError(_('Appointments is already invoiced.'))
            if prescription.name.partner_id.id:
                if prescription.name.partner_id.property_account_receivable_id.id:
                    invoice_data['partner_id'] = prescription.name.partner_id.id
                    invoice_data['invoice_types'] = 'prescription'
                    invoice_data[
                        'fiscal_position_id'] = prescription.name.partner_id.property_account_position_id and prescription.name.patient.partner_id.property_account_position_id.id or False
                    invoice_data[
                        'invoice_payment_term_id'] = prescription.name.partner_id.property_payment_term_id and prescription.name.patient.partner_id.property_payment_term_id.id or False
                    invoice_data['move_type'] = 'out_invoice'
                else:
                    raise UserError(_('Account is not added for Patient.'))

            if prescription.prescription_line:
                for pres_line in prescription.prescription_line:
                    account_id = pres_line.medicament.product_medicament_id.product_tmpl_id.property_account_income_id.id
                    if not account_id:
                        account_id = pres_line.medicament.product_medicament_id.categ_id.property_account_income_categ_id.id
                    if not account_id:
                        raise UserError(_('Account is not added for test.'))
                    prods_lines.append((0, 0, {'product_id': pres_line.medicament.product_medicament_id.id,
                                               'name': pres_line.medicament.product_medicament_id.name,
                                               'quantity': pres_line.quantity,
                                               'account_id': account_id,
                                               'price_unit': pres_line.medicament.product_medicament_id.lst_price}))
                invoice_data['invoice_line_ids'] = prods_lines
                invoice_id = invoice_obj.create(invoice_data)
                inv_id_list.append(invoice_id.id)
                prescription.write({'inv_id': invoice_id.id, 'invoice_status': 'invoiced'})

            else:
                raise UserError(_('You need to have at least one prescription item in your invoice'))

        imd = self.env['ir.model.data']
        res_id = imd._xmlid_to_res_id('account.view_move_tree')
        res_id_form = imd._xmlid_to_res_id('account.view_move_form')
        result = {
            'name': 'Created invoice',
            'type': 'tree',
            'views': [(res_id, 'tree'), (res_id_form, 'form')],
            'target': 'current',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
        }
        if inv_id_list:
            result['domain'] = "[('id','in',%s)]" % inv_id_list
            result['res_id'] = inv_id_list[0]
        return result

#     def default_get(self, cr, uid, fields, context=None):
#          if context is None: context = {}
#          res = {}
#          if context.has_key('name'):
#               move_ids = context.get ('name')
#               res.update(name=move_ids)
#          if context.has_key('prescription_date'):
#               p_date = context.get ('prescription_date')
#                
#                
#               res.update(prescription_date=p_date)
#          if context.has_key('physician_id'):
#               phy_ids = context.get ('physician_id')
#               if phy_ids==False:
#                   raise  osv.except_osv(_('UserError'), _('No Doctor Added'))
#               else:
#                   p= self.pool.get('medical.physician').browse(cr,uid,phy_ids)
#                   res.update(physician_id=p.name.id)
#            
#          res.update(user_id=uid)
#          return res
     
