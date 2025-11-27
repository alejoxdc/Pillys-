# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class MedicalImagingTestType(models.Model):
    _name = "medical.imaging.test.type"
    
    name = fields.Char('Name', size=128, required=True)
    code = fields.Char('Code', size=128, required=True)


class MedicalImagingTest(models.Model):
    _name = "medical.imaging.test"
    
    name = fields.Char('Name', size=128, required=True)
    code = fields.Char('Code', size=128, required=True)
    product_id = fields.Many2one('product.product', 'Service', required=True, domain=[('type', '=', 'service')])
    test_type_id = fields.Many2one('medical.imaging.test.type', 'Type', required=True)


class MedicalImagingTestRequest(models.Model):
    _name = "medical.imaging.test.request"
    
#     @api.model
#     def _get_default_doctor(self):
#         doc_ids = None
#         partner_ids = self.env['res.partner'].search([('user_id', '=', self.env.user.id),('is_doctor', '=', True)],limit=1)
#         if partner_ids:
#             doc_ids = self.env['medical.physician'].search([('name', 'in', partner_ids)])
#             if doc_ids:
#                 return doc_ids.id
#         return doc_ids

    patient_id = fields.Many2one('medical.patient', 'Patient', required=True)
    test_date = fields.Datetime('Test Date', required=True, default=fields.Datetime.now)
    test_id = fields.Many2one('medical.imaging.test', 'Test', required=True)
    test_price = fields.Integer('Test Price')
    no_invoice = fields.Boolean('Invoice exempt', default=False)
    # physician_id =  fields.Many2one('medical.physician','Physician', required=True,default='_get_default_doctor' )
    physician_id = fields.Many2one('medical.physician', 'Physician', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancel', 'Cancel')], 'State', readonly=True, default='draft')
    comments = fields.Text('Comments')
    urgent = fields.Boolean('Urgent')
    name = fields.Char('Request', size=128, readonly=True, default=lambda self: _('New'))
    validity_status = fields.Selection([
        ('invoiced', 'Invoiced'),
        ('tobe', 'To be Invoiced')], 'Status', default='tobe', copy=False)
    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
    )

    def create_invoice(self):
        invoice_obj = self.env['account.move']
        invoice_data = {}
        prods_lines = []
        inv_id_list = []
        for request in self:
            if request.state == 'draft':
                raise UserError(_('The request is in Draft State. First Confirm it.'))
            if request.validity_status == 'invoiced':
                raise UserError(_('Imaging request is already invoiced.'))
            if request.no_invoice:
                raise UserError(_('Imaging request is invoice exempt.'))
            if request.test_price == 0:
                raise UserError(_('Test price should not be 0.'))
            if request.validity_status == 'tobe' and request.patient_id.partner_id.id and not request.no_invoice:
                if request.patient_id.partner_id.property_account_receivable_id.id:
                    invoice_data['partner_id'] = request.patient_id.partner_id.id
                    invoice_data['invoice_types'] = 'imaging'
                    invoice_data['fiscal_position_id'] = request.patient_id.partner_id.property_account_position_id and request.patient_id.partner_id.property_account_position_id.id or False
                    invoice_data['invoice_payment_term_id'] = request.patient_id.partner_id.property_payment_term_id and request.patient_id.partner_id.property_payment_term_id.id or False
                    invoice_data['move_type'] = 'out_invoice'
                else:
                    raise UserError(_('Account is not added for Patient.'))
                account_id = request.test_id.product_id.property_account_income_id.id
                if not account_id:
                    account_id = request.test_id.product_id.categ_id.property_account_income_categ_id.id
                if not account_id:
                    raise UserError(_('Account is not added for set for request.'))
                prods_lines.append((0,None,{'product_id':request.test_id.product_id.id,
                                    'name':request.test_id.product_id.name,
                                    'quantity':1,
                                    'account_id':account_id,
                                    'price_unit':request.test_price}))
                invoice_data['invoice_line_ids'] = prods_lines
                invoice_id = invoice_obj.create(invoice_data)
                inv_id_list.append(invoice_id.id)
                request.write({'invoice_id': invoice_id.id, 'validity_status': 'invoiced'})
    
    def done(self):
        image_result = self.env['medical.imaging.test.result']
        for obj in self:
            test_id_list = []
            vals = {
                'patient_id': self.patient_id.id,
                'test_date': self.test_date,
                'physician_id': self.physician_id.id,
                'test_id': self.test_id.id,
                'comments': self.comments,
                'request_id': self.id
                }
            test_id = image_result.create(vals)
            test_id_list.append(test_id.id)
            
        self.write({'state': 'done'})
        imd = self.env['ir.model.data']
        res_id = imd._xmlid_to_res_id('medical_imaging_test_result_tree')
        res_id_form = imd._xmlid_to_res_id('medical_imaging_test_result_form')
        result = {
            'name': 'Imaging Request',
            'type': 'tree',
            'views': [(res_id, 'tree'),(res_id_form, 'form')],
            'target': 'current',
            'res_model': 'medical.imaging.test.result',
            'type': 'ir.actions.act_window',
        }
        if test_id_list:
            result['domain'] = "[('id','in',%s)]" % test_id_list
        return result

    def confirm(self):
        self.write({'state': 'confirmed'})
        
    def cancel(self):
        self.write({'state': 'cancel'})
            
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('medical.imaging.test.request') or 'New'
        result = super(MedicalImagingTestRequest, self).create(vals)
        self._cr.execute('insert into pat_img_rel(patients,imgid) values (%s,%s)', (vals['patient_id'], result.id))
        return result


class MedicalImagingTestResult(models.Model):
    _name = "medical.imaging.test.result"
    
    patient_id = fields.Many2one('medical.patient', 'Patient', readonly=True)
    test_date = fields.Datetime('Date', required=True, default=fields.Datetime.now)
    request_date = fields.Datetime('Request Date')
    test_id = fields.Many2one('medical.imaging.test', 'Test', readonly=True)
    request_id = fields.Many2one('medical.imaging.test.request', 'Test request', readonly=True)
    physician_id = fields.Many2one('medical.physician', 'Physician', required=True)
    comments = fields.Text('Comments')
    name = fields.Char('Number', size=128, readonly=True, default=lambda self: _('New'))
    images = fields.One2many('ir.attachment', 'request_attach_id', 'Images')
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('medical.imaging.test.result') or 'New'
        result = super(MedicalImagingTestResult, self).create(vals)
        return result


class IrAttachment(models.Model):
    """
    Form for Attachment details
    """
    _inherit = "ir.attachment"
    _name = "ir.attachment"
    
    request_attach_id = fields.Many2one('medical.imaging.test.result', 'Result')
