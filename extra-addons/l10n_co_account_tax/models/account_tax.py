# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2022 INNOVATECSA S.A.S (<http://www.innovatecsa.com>)
#
##############################################################################

from odoo import api, fields, models, _
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import ValidationError

class AccountFiscalYear(models.Model):
    _inherit = "account.fiscal.year"

    fiscal_unit = fields.Float('Vr. UVT', help="Valor de la UVT para el año fiscal")


class account_tax(models.Model):
    _name = "account.tax"
    _inherit = "account.tax"

    in_order = fields.Boolean('Incluir en pedido', help='Si esta chequeado se incluye en el calculo de impuestos en la orden o pedido', default=False)
    python_invoice = fields.Text('Invoice Python Code',help='Python code to apply or not the tax at invoice level', default='''result = base > fiscal_unit * base_uvt_qty''')
    applicable_invoice = fields.Boolean('Applicable Invoice', help='Use python code to apply this tax code at invoice', default=False)
    notprintable = fields.Boolean("Not Printable in Invoice", help="Check this box if you don't want any tax related to this tax code to appear on invoices", default=False)
    base_uvt_qty = fields.Float('Base en UVT', help="Base en UVT", required=True, default=0)
    
    @api.model
    def _applicable_invoice(self, tax_id, move_id, amount, base):
    
        localdict = {'amount':amount, 'base':abs(base)}
        tax = self.browse(tax_id)
        
        if tax.applicable_invoice:
            invoice = self.env['account.move'].browse(move_id)
            
            fiscal_unit = 0.0            
            current_date = invoice.invoice_date or fields.Date.context_today(self)
            date_str = current_date.strftime(DEFAULT_SERVER_DATE_FORMAT)

            if invoice.company_id:
               fiscalyear = self.env['account.fiscal.year'].search([
                 ('company_id', '=', invoice.company_id.id),
                 ('date_from', '<=', date_str),
                 ('date_to', '>=', date_str),
               ], limit=1)
            else:
               fiscalyear = self.env['account.fiscal.year'].search([
                 ('date_from', '<=', date_str),
                 ('date_to', '>=', date_str),
               ], limit=1)

            if fiscalyear:
               fiscal_unit = fiscalyear[0].fiscal_unit
            else:   
               raise ValidationError("No existe ejercicio fiscal para el día %s" % (date_str))

            localdict['fiscal_unit'] = fiscal_unit
            localdict['base_uvt_qty'] = tax.base_uvt_qty
            localdict['invoice'] = invoice
            localdict['partner'] = invoice.partner_id
            exec (tax.python_invoice, localdict)
			
        return localdict.get('result', True)


