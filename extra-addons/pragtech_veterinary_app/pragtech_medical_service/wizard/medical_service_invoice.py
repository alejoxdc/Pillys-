# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo import api, fields, models, tools, _


class medical_service_invoice_wizard(models.TransientModel):
    _name = 'medical.service.invoice.wizard'
    _description = 'medical service Invoice'

    def create_invoice(self, ):
        invoice_obj = self.env['account.move']
        service_obj = self.env['medical.health_service']
        context = dict(self._context or {})
        prescriptions = context.get('active_ids')
        services = service_obj.browse(context['active_ids'])
        journal_obj = self.env['account.journal']
        journal_ids = journal_obj.search([('type', '=', 'sale')], limit=1)
        for service in services:
            if service.state == 'invoiced':
                raise UserError(_('Service %s is already invoiced') % (service.name))
            if service.state == 'draft':
                raise UserError(_('Service %s can not be invoiced as it is in draft state.') % (service.name))
            invoice_ex = True
            for line in service.service_line:

                if line.to_invoice:
                    invoice_ex = False
            if invoice_ex == False:
                type = 'out_invoice'
                acc_id = service.patient.name.property_account_receivable_id.id
                inv = {
                    'name': service.name,
                    'origin': service.name,
                    'type': type,
                    'reference': "Medical Service Invoice",
                    'account_id': acc_id,
                    'partner_id': service.patient.name.id,
                    'currency_id': service.patient.name.company_id.currency_id.id,
                    'journal_id': len(journal_ids) and journal_ids[0].id or False,
                }
                invoice_id = self.env['account.move'].create(inv)
                for line in service.service_line:
                    if line.to_invoice:
                        if line.product.categ_id:
                            a = line.product.categ_id.property_account_income_categ_id.id
                            if not a:
                                raise ValidationError(
                                    _('There is no expense account defined for this product: "%s" (id:%d)') % (
                                    line.product.name, line.product.id,))
                        else:
                            a = self.env['ir.property'].get('property_account_income_categ_id', 'product.category').id
                        il = {
                            'name': line.product.name,
                            'account_id': a,
                            'price_unit': line.product.list_price,
                            'quantity': line.qty,
                            'origin': service.name,
                            'invoice_id': invoice_id.id,
                            #                                 'pay_date':service.service_date,
                        }
                        l = self.env['account.move.line'].create(il)
                service.write({'inv_id': invoice_id.id})

            service.write({'state': 'invoiced'})
        return {
            'name': 'Create Invoice',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window'
        }

# medical_service_invoice_wizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
