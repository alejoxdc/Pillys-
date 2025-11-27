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


class make_medical_appointment_invoice(models.TransientModel):
    _name = "medical.appointment.invoice"
    _inherit = "medical.appointment.invoice"

    def create_invoice(self):
        invoice_obj = self.env['account.move']
        appointment_obj = self.env['medical.appointment']
        flag1 = False
        context = dict(self._context or {})
        apps = context.get('active_ids')
        pats = []
        for app_id in apps:
            flag1 = (appointment_obj.browse(app_id).patient.partner_id.is_pet)
            pats.append(appointment_obj.browse(app_id).patient.partner_id.id)

        if pats.count(pats[0]) == len(pats):
            invoice_data = {}
            for app_id in apps:
                appointment = appointment_obj.browse(app_id)

                # Check if the appointment is invoice exempt, and stop the invoicing process
                if appointment.no_invoice:
                    raise UserError(_('The appointment is invoice exempt'))
                if appointment.state == 'draft':
                    raise UserError(_('At least one of the selected appointment is in Draft state. First Confirm It.'))

                if appointment.validity_status == 'invoiced':
                    if len(apps) > 1:
                        raise UserError(_('At least one of the selected appointments is already invoiced'))
                    else:
                        raise UserError(_('Appointment already invoiced'))
                if appointment.validity_status == 'no':
                    if len(apps) > 1:
                        raise UserError(_('At least one of the selected appointments can not be invoiced'))
                    else:
                        raise UserError(_('You can not invoice this appointment'))

            if flag1 == True and appointment.patient.partner_id.id:
                invoice_data['partner_id'] = appointment.patient.partner_id.owner_name.id
                res = appointment.patient.partner_id.address_get(['contact', 'invoice'])
                # invoice_data['address_contact_id'] = res['contact']
                # invoice_data['address_invoice_id'] = res['invoice']
                # invoice_data['account_id'] = appointment.patient.partner_id.owner_name.property_account_receivable_id.id
                invoice_data[
                    'fiscal_position_id'] = appointment.patient.partner_id.owner_name.property_account_position_id and appointment.patient.partner_id.property_account_position_id.id or False
                invoice_data[
                    'invoice_payment_term_id'] = appointment.patient.partner_id.owner_name.property_payment_term_id and appointment.patient.partner_id.property_payment_term_id.id or False
                invoice_data['move_type'] = 'out_invoice'
            elif flag1 == False and appointment.patient.partner_id.id:
                invoice_data['partner_id'] = appointment.patient.partner_id.id
                res = self.pool.get('res.partner').address_get([appointment.patient.partner_id.id],
                                                               ['contact', 'invoice'])
                # invoice_data['address_contact_id'] = res['contact']
                # invoice_data['address_invoice_id'] = res['invoice']
                # invoice_data['account_id'] = appointment.patient.partner_id.property_account_receivable_id.id
                invoice_data[
                    'fiscal_position'] = appointment.patient.partner_id.property_account_position_id and appointment.patient.partner_id.property_account_position_id.id or False
                invoice_data[
                    'invoice_payment_term_id'] = appointment.patient.partner_id.property_payment_term_id and appointment.patient.partner_id.property_payment_term_id.id or False

            prods_data = {}
            for app_id in apps:
                appointment = appointment_obj.browse(app_id)
                logging.debug('appointment = %s; appointment.consultations = %s', appointment,
                              appointment.consultations)
                if appointment.consultations:
                    logging.debug('appointment.consultations = %s; appointment.consultations.id = %s',
                                  appointment.consultations, appointment.consultations.id)
                    #                     if prods_data.has_key(appointment.consultations.id):
                    if appointment.consultations.id in prods_data:

                        prods_data[appointment.consultations.id]['quantity'] += 1
                    else:
                        a = appointment.consultations.product_tmpl_id.property_account_income_id.id
                        if not a:
                            a = appointment.consultations.categ_id.property_account_income_categ_id.id
                        prods_data[appointment.consultations.id] = {'product_id': appointment.consultations.id,
                                                                    'name': appointment.consultations.name,
                                                                    'quantity': 1,
                                                                    'account_id': a,
                                                                    'price_unit': appointment.consultations.lst_price}
                else:
                    raise UserError(_('No consultation service is connected with the selected appointments'))

            product_lines = []
            for prod_id, prod_data in prods_data.items():
                product_lines.append((0, None, {'product_id': prod_data['product_id'],
                                                'name': prod_data['name'],
                                                'quantity': prod_data['quantity'],
                                                'account_id': prod_data['account_id'],
                                                'price_unit': prod_data['price_unit']}))

            invoice_data['invoice_line_ids'] = product_lines
            invoice_id = invoice_obj.create(invoice_data)
            view_id = self.env['ir.ui.view'].search([('name', '=', 'account.move.form')])
            appointment = appointment_obj.browse(apps[0])
            appointment.write({'inv_id': invoice_id.id, 'validity_status': 'invoiced'})
            result = {
                'name': 'Create invoice',
                'view_type': 'form',
                'view_id': view_id[0].id,
                'view_mode': 'form',
                'res_id': invoice_id.id,
                'res_model': 'account.move',
                'context': context,
                'type': 'ir.actions.act_window'
            }


        else:
            raise UserError(_('When multiple appointments are selected, patient must be the same'))
