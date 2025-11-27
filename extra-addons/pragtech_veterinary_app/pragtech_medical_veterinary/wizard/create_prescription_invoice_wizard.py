# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010  Adrián Bernardi, Mario Puntin
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import api, fields, models, tools, _
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, RedirectWarning, ValidationError
import logging

_logger = logging.getLogger(__name__)


class create_medical_prescription_invoice(models.TransientModel):
    _name = "medical.prescription.invoice"
    _inherit = "medical.prescription.invoice"

    def create_prescription_invoice(self):

        invoice_obj = self.env['account.move']
        pres_request_obj = self.env['medical.prescription.order']

        #        prescriptions = ids
        # Don't use this. It will be 1 (and it would go to the invoice status of the first prescription )

        # To get the IDs of the prescriptions, use the context value array for active_ids

        context = dict(self._context or {})
        prescriptions = context.get('active_ids')

        pats = []

        for pres_id in prescriptions:
            pres = pres_request_obj.browse(pres_id)
            pats.append(pres.name)
            logging.debug('pres = %s; pats = %s', repr(pres), repr(pats))

        if pats.count(pats[0]) == len(pats):
            invoice_data = {}
            for pres_id in prescriptions:
                pres = pres_request_obj.browse(pres_id)

                # Check if the prescription is invoice exempt, and stop the invoicing process
                if pres.no_invoice:
                    raise UserError(_('The prescription is invoice exempt'))
                #                 if pres.state == 'draft' :
                #                     raise  osv.except_osv(_('UserError'), _('At least one of the selected prescription is in Draft state. First Confirm It.'))
                if pres.invoice_status == 'invoiced':
                    logging.debug('pres.invoice_status = %s', repr(pres.invoice_status))
                    if len(prescriptions) > 1:
                        raise UserError(_('At least one of the selected prescriptions is already invoiced'))
                    else:
                        raise UserError(_('Prescription already invoiced'))
                if pres.invoice_status == 'no':
                    if len(prescriptions) > 1:
                        raise UserError(_('At least one of the selected prescriptions can not be invoiced'))
                    else:
                        raise UserError(_('You can not invoice this prescription'))

            logging.debug('pres.name = %s', repr(pres.name))

            if pres.name.partner_id.is_pet == True and pres.name.partner_id.id:
                invoice_data['partner_id'] = pres.name.partner_id.id
                res = pres.name.partner_id.address_get(['contact', 'invoice'])


            elif pres.name.partner_id.is_pet == False and pres.name.partner_id.id:
                invoice_data['partner_id'] = pres.name.name.id
                res = pres.name.partner_id.address_get(['contact', 'invoice'])

            prods_data = {}
            for pres_id in prescriptions:
                pres = pres_request_obj.browse(pres_id)
                logging.debug('pres.name = %s; pres.prescription_line = %s', pres.name, pres.prescription_line)

                # Check for empty prescription lines

                if not pres.prescription_line:
                    raise UserError(_('You need to have at least one prescription item in your invoice'))

                for pres_line in pres.prescription_line:
                    logging.debug('pres_line = %s; pres_line.medicament.name = %s; pres_line.quantity = %s', pres_line,
                                  pres_line.medicament.name, pres_line.quantity)

                    #                     if prods_data.has_key(pres_line.medicament.name):
                    if pres_line.medicament.name in prods_data:
                        prods_data[pres_line.medicament.name]['quantity'] += pres_line.quantity
                    else:
                        a = pres_line.medicament.product_medicament_id.product_tmpl_id.property_account_income_id.id
                        if not a:
                            a = pres_line.medicament.product_medicament_id.categ_id.property_account_income_categ_id.id

                        prods_data[pres_line.medicament.name] = {
                            'product_id': pres_line.medicament.product_medicament_id.id,
                            'name': pres_line.medicament.product_medicament_id.name,
                            'quantity': pres_line.quantity,
                            'account_id': a,
                            'price_unit': pres_line.medicament.product_medicament_id.lst_price}

            product_lines = []
            for prod_id, prod_data in prods_data.items():
                logging.debug('product_id = %s', repr(prod_data['product_id']))
                product_lines.append((0, 0, {'product_id': prod_data['product_id'],
                                             'name': prod_data['name'],
                                             'quantity': prod_data['quantity'],
                                             'account_id': prod_data['account_id'],
                                             'price_unit': prod_data['price_unit']}))

            invoice_data['invoice_line_ids'] = product_lines
            invoice_id = invoice_obj.create(invoice_data)
            pres_brw = pres_request_obj.browse(prescriptions[0])
            pres_brw.write({'inv_id': invoice_id.id, 'invoice_status': 'invoiced'})

            return {
                'domain': "[('id','=', " + str(invoice_id.id) + ")]",
                'name': 'Create Prescription Invoice',
                'view_mode': 'tree,form',
                'res_model': 'account.move',
                'type': 'ir.actions.act_window'
            }

        else:
            raise UserError(_('When multiple prescriptions are selected, patient must be the same'))
