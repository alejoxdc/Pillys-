# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError


class CreateImagingTestInvoice(models.TransientModel):
    _name = 'medical.imaging.test.invoice'
    
    def create_imaging_invoice(self):
        test_request_obj = self.env['medical.imaging.test.request']
        invoice_obj = self.env['account.move']
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []
        invoice_data = {}
        prods_lines = []
        inv_id_list = []
        partner_list = []
            
        for record in test_request_obj.browse(active_ids):
            if record.state == 'draft':
                raise UserError(_('At least one of the selected imaging test is in Draft State. First Confirm it.'))
            if record.no_invoice:
                raise UserError(_('At least one of the selected imaging test is invoice exempt.'))
            if record.validity_status == 'invoiced':
                raise UserError(_('At least one of the selected imaging test is already invoiced.'))
            if record.patient_id.partner_id.id:
                if record.patient_id.partner_id.property_account_receivable_id.id:
                    invoice_data['partner_id'] = record.patient_id.partner_id.id
                    invoice_data['account_id'] = record.patient_id.partner_id.property_account_receivable_id.id
                    invoice_data['fiscal_position_id'] = record.patient_id.partner_id.property_account_position_id and record.patient_id.partner_id.property_account_position_id.id or False
                    invoice_data['payment_term_id'] = record.patient_id.partner_id.property_payment_term_id and record.patient_id.partner_id.property_payment_term_id.id or False
                else:
                    raise UserError(_('Account is not added for Patient.'))
            
            if record.test_id.product_id:
                account_id = record.test_id.product_id.product_tmpl_id.property_account_income_id.id
                if not account_id:
                    account_id = record.test_id.product_id.categ_id.property_account_income_categ_id.id
                if not account_id:
                    raise UserError(_('Account is not added for set for Test.'))
                prods_lines.append((0, 0, {
                    'product_id': record.test_id.product_id.id,
                    'name': record.test_id.name,
                    'quantity': 1,
                    'account_id': account_id,
                    'price_unit': record.test_price
                }))
        invoice_data['invoice_line_ids'] = prods_lines
        invoice_id = invoice_obj.create(invoice_data)
        inv_id_list.append(invoice_id.id)
        for imaging in test_request_obj.browse(active_ids):
            imaging.write({'inv_id': invoice_id.id, 'validity_status': 'invoiced'})
        imd = self.env['ir.model.data']
        res_id = imd._xmlid_to_res_id('invoice_tree')
        res_id_form = imd._xmlid_to_res_id('invoice_form')
        result = {
            'name': 'Create invoice',
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
