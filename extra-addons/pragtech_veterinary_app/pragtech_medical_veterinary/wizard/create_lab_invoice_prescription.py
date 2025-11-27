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


class create_test_invoice(models.TransientModel):
    _name = 'medical.lab.test.invoice'

    def create_lab_invoice(self):

        invoice_obj = self.env['account.move']
        test_request_obj = self.env['medical.patient.lab.test']

        context = dict(self._context or {})
        tests = context.get('active_ids')
        logging.debug('tests = %s', repr(tests))

        pats = []
        for test_id in tests:
            # pats.append(test_request_obj.browse(cr, uid, test_id).patient_id)
            cur_test = test_request_obj.browse(test_id)
            logging.debug('cur_test = %s; pats = %s', repr(cur_test), repr(pats))
            pats.append(cur_test.patient_id)

        logging.debug('pats = %s', repr(pats))

        if pats.count(pats[0]) == len(pats):
            invoice_data = {}
            for test_id in tests:

                # test = self.browse(cr, uid, test_id)
                test = test_request_obj.browse(test_id)

                logging.debug('test = %s', repr(test))
                if test.state == "draft":
                    raise UserError(_('At least one of the selected lab test is in Draft State. First Confirm it.'))
                if test.validity_status == 'invoiced':
                    if len(tests) > 1:
                        raise UserError(_('At least one of the selected lab tests is already invoiced'))
                    else:
                        raise UserError(_('Lab test already invoiced'))
                if test.validity_status == 'no':
                    if len(tests) > 1:
                        raise UserError(_('At least one of the selected lab tests can not be invoiced'))
                    else:
                        raise UserError(_('You can not invoice this lab test'))

            logging.debug('test.patient_id = %s; test.patient_id.id = %s', test.patient_id, test.patient_id.id)

            if test.patient_id.partner_id.is_pet == True and test.patient_id.partner_id.id:
                invoice_data['partner_id'] = test.patient_id.partner_id.owner_name.id
                res = test.patient_id.partner_id.address_get(['contact', 'invoice'])


            elif test.patient_id.partner_id.is_pet == False and test.patient_id.partner_id.id:
                invoice_data['partner_id'] = test.patient_id.partner_id.id
                res = self.env['res.partner'].address_get([test.patient_id.partner_id.id], ['contact', 'invoice'])

            prods_data = {}

            tests = context.get('active_ids')
            logging.debug('tests = %s', repr(tests))

            for test_id in tests:
                test = test_request_obj.browse(test_id)
                logging.debug('test.name = %s; test.name.product_id = %s; test.name.product_id.id = %s', test.name,
                              test.name.product_id, test.name.product_id.id)

                if prods_data.get(test.name.product_id.id):
                    logging.debug('prods_data = %s; test.name.product_id.id = %s', prods_data, test.name.product_id.id)
                    prods_data[test.name.product_id.id]['quantity'] += 1
                else:
                    logging.debug('test.name.product_id.id = %s', test.name.product_id.id)
                    a = test.name.product_id.product_tmpl_id.property_account_income_id.id
                    if not a:
                        a = test.name.product_id.categ_id.property_account_income_categ_id.id
                    prods_data[test.name.product_id.id] = {'product_id': test.name.product_id.id,
                                                           'name': test.name.product_id.name,
                                                           'quantity': 1,
                                                           'account_id': a,
                                                           'price_unit': test.name.product_id.lst_price}
                    logging.debug('prods_data[test.name.product_id.id] = %s', prods_data[test.name.product_id.id])

            product_lines = []
            for prod_id, prod_data in prods_data.items():
                product_lines.append((0, 0, {'product_id': prod_data['product_id'],
                                             'name': prod_data['name'],
                                             'quantity': prod_data['quantity'],
                                             'account_id': prod_data['account_id'],
                                             'price_unit': prod_data['price_unit']}))

            invoice_data['invoice_line_ids'] = product_lines
            invoice_id = invoice_obj.create(invoice_data)
            test_obj = test_request_obj.browse(tests[0])
            test_obj.write({'validity_status': 'invoiced'})

            return {
                'domain': "[('id','=', " + str(invoice_id.id) + ")]",
                'name': 'Create Lab Invoice',
                'view_mode': 'tree,form',
                'res_model': 'account.move',
                'type': 'ir.actions.act_window'
            }

        else:
            raise UserError(_('When multiple lab tests are selected, patient must be the same'))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
