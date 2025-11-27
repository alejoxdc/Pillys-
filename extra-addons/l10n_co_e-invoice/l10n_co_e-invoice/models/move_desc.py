
from odoo import api, fields, models,_
from odoo.exceptions import UserError, ValidationError
import logging
from pprint import pprint
import sys
from contextlib import ExitStack, contextmanager 
_logger = logging.getLogger(__name__)
from odoo.tools import (
    date_utils,
    email_re,
    email_split,
    float_compare,
    float_is_zero,
    float_repr,
    format_amount,
    format_date,
    formatLang,
    frozendict,
    get_lang,
    groupby,
    index_exists,
    is_html_empty,
)

class KsGlobalTaxInvoice(models.Model):
    _inherit = "account.move"
    
    enable_invoice_discount = fields.Selection(selection=[
                                                ('value', 'Por Valor'),
                                                ('percent', 'Por Porcentaje'),
                                            ],string='Descuento Pie de Factura',default='percent')
    razon_descuento = fields.Char('Razon del Descuento',default='Servicios')
    type_invoice_discount = fields.Selection(selection=[('linea', 'Por linea'),
                                                        ('global', 'Global'),
                                                    ],string='Descuento Pie de Factura',default='global')

    invoice_discount = fields.Monetary(string='Desc. De Factura $', store=True)
    invoice_discount_view = fields.Monetary(related="invoice_discount",string='Desc. De Factura',store=False)
    invoice_discount_percent = fields.Float(string='Desc. De Factura %', readonly=True, store=True)
    invoice_discount_tax = fields.Selection(selection=[('00', 'Descuento Base Impuesto'),
                                                        ('01', 'Descuento Sin Base Impuesto')],string='Motivo de Descuento',default='00')
    sales_discount_account = fields.Many2one('account.account', related='company_id.sales_discount_account', string="Sales Tax Account")
    purchase_discount_account = fields.Many2one('account.account', related='company_id.purchase_discount_account',string="Purchase Tax Account")

    @api.constrains('invoice_discount_percent',)
    def ks_check_tax_value(self):
        if (self.invoice_discount_percent > 100 or self.invoice_discount_percent < 0):
            raise ValidationError('No puede ingresar un valor porcentual mayor que 100 o menor que 0.')

    def _recompute_global_discount_lines(self):
        ''' Handle the global discount feature on invoices. '''
        self.ensure_one()
        def _apply_global_discount(discount_amount, discount_line):
            ''' Apply the global discount.
            :param self:                    The current account.move record.
            :param discount_amount:         The discount amount to apply.
            :param discount_line:           The existing discount line.
            :return:                        The newly created discount line.
            '''
           
            discount_line_vals = {
                'balance': discount_amount,
                'partner_id': self.partner_id.id,
                'move_id': self.id,
                'currency_id': self.currency_id.id,
                'company_id': self.company_id.id,
                'company_currency_id': self.company_id.currency_id.id,
                'display_type': 'discount',
                'discount_okay': True,
            }

            if self.move_type in ('out_invoice', 'in_refund'):
                account_id = self.company_id.sales_discount_account.id
                discount_line_vals.update({
                    'name': self.razon_descuento,
                    'account_id': account_id,
                    'debit': abs(discount_amount),
                    'credit': 0,
                })
            elif self.move_type in ('in_invoice', 'out_refund'):
                account_id = self.company_id.purchase_discount_account.id
                discount_line_vals.update({
                    'name': self.razon_descuento,
                    'account_id': account_id,
                    'debit': 0,
                    'credit': abs(discount_amount),
                })

            # Create or update the global discount line.
            if discount_line:
                discount_line.write(discount_line_vals)
            else:
                discount_line = self.env['account.move.line'].create(discount_line_vals)

        existing_discount_line = self.line_ids.filtered(lambda line: line.display_type == 'discount' and line.discount_okay)

        # The global discount has been removed.
        if not self.invoice_discount:
            existing_discount_line.unlink()
            return

        discount_amount = self.invoice_discount

        _apply_global_discount(discount_amount, existing_discount_line)

    @contextmanager
    def _sync_rounding_lines(self, container):
        yield
        for invoice in container['records']:
            if invoice.state != 'posted':
                invoice._recompute_global_discount_lines()
                invoice._recompute_cash_rounding_lines()

    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.balance',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id',
        'invoice_discount',
        'state')
    def _compute_amount(self):
        for move in self:
            total_untaxed, total_untaxed_currency = 0.0, 0.0
            total_tax, total_tax_currency = 0.0, 0.0
            total_residual, total_residual_currency = 0.0, 0.0
            total, total_currency = 0.0, 0.0

            for line in move.line_ids:
                if move.is_invoice(True):
                    # === Invoices ===
                    if line.display_type == 'tax' or (line.display_type == 'rounding' and line.tax_repartition_line_id):
                        # Tax amount.
                        total_tax += line.balance
                        total_tax_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.display_type in ('product', 'rounding') or line.discount_okay:
                        # Untaxed amount.
                        total_untaxed += line.balance
                        total_untaxed_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.display_type == 'payment_term':
                        # Residual amount.
                        total_residual += line.amount_residual
                        total_residual_currency += line.amount_residual_currency
                else:
                    # === Miscellaneous journal entry ===
                    if line.debit:
                        total += line.balance
                        total_currency += line.amount_currency

            sign = move.direction_sign
            move.amount_untaxed = sign * total_untaxed_currency
            move.amount_tax = sign * total_tax_currency
            move.amount_total = sign * total_currency
            move.amount_residual = -sign * total_residual_currency
            move.amount_untaxed_signed = -total_untaxed
            move.amount_tax_signed = -total_tax
            move.amount_total_signed = abs(total) if move.move_type == 'entry' else -total
            move.amount_residual_signed = total_residual
            move.amount_total_in_currency_signed = abs(move.amount_total) if move.move_type == 'entry' else -(sign * move.amount_total)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    price_unit_with_discount = fields.Float(compute='_compute_price_unit_with_discount', store=True)
    discount_line = fields.Float('Descuento C. ($)', store=True)
    discount_okay = fields.Boolean('Linea de descuento')
    @api.depends('price_unit', 'discount', 'move_id.invoice_discount', 'move_id.invoice_discount_percent', 'discount_line', 'move_id.invoice_line_ids')
    def _compute_price_unit_with_discount(self):
        for rec in self:
            total_invoice_amount = sum(line.price_unit * line.quantity for line in rec.move_id.invoice_line_ids)
            if total_invoice_amount == 0:
                rec.price_unit_with_discount = rec.price_unit * (1 - (rec.discount / 100.0))
                continue 
            if rec.move_id.type_invoice_discount == 'linea':
                rec.price_unit_with_discount = rec.price_unit * (1 - ((rec.discount + rec.discount_line) / 100.0))
            else:
                rec.price_unit_with_discount = rec._get_price_unit_with_discount(total_invoice_amount)

    def _get_price_unit_with_discount(self, total_invoice_amount):
        price_unit_after_line_discount = self.price_unit * (1 - ((self.discount) / 100.0))
        line_proportion = (self.price_unit * self.quantity) / total_invoice_amount
        line_share_of_invoice_discount = self.move_id.invoice_discount * line_proportion
        discount_per_unit = line_share_of_invoice_discount / (self.quantity if self.quantity != 0 else 1)
        price_unit_with_discount = price_unit_after_line_discount - discount_per_unit

        return price_unit_with_discount
    

    # @api.depends('tax_ids', 'currency_id', 'partner_id', 'analytic_distribution', 'balance', 'partner_id', 'move_id.partner_id', 'price_unit', 'quantity')
    # def _compute_all_tax(self):
    #     for line in self:
    #         sign = line.move_id.direction_sign
    #         if line.display_type == 'tax':
    #             line.compute_all_tax = {}
    #             line.compute_all_tax_dirty = False
    #             continue
    #         if line.display_type == 'product' and line.move_id.is_invoice(True):
    #             amount_currency = sign * line.price_unit_with_discount
    #             handle_price_include = True
    #             quantity = line.quantity
    #         else:
    #             amount_currency = line.amount_currency
    #             handle_price_include = False
    #             quantity = 1
    #         compute_all_currency = line.tax_ids.compute_all(
    #             amount_currency,
    #             currency=line.currency_id,
    #             quantity=quantity,
    #             product=line.product_id,
    #             partner=line.move_id.partner_id or line.partner_id,
    #             is_refund=line.is_refund,
    #             handle_price_include=handle_price_include,
    #             include_caba_tags=line.move_id.always_tax_exigible,
    #             fixed_multiplicator=sign,
    #         )
    #         rate = line.amount_currency / line.balance if line.balance else 1
    #         line.compute_all_tax_dirty = True
    #         line.compute_all_tax = {
    #             frozendict({
    #                 'tax_repartition_line_id': tax['tax_repartition_line_id'],
    #                 'group_tax_id': tax['group'] and tax['group'].id or False,
    #                 'account_id': tax['account_id'] or line.account_id.id,
    #                 'currency_id': line.currency_id.id,
    #                 'analytic_distribution': (tax['analytic'] or not tax['use_in_tax_closing']) and line.analytic_distribution,
    #                 'tax_ids': [(6, 0, tax['tax_ids'])],
    #                 'tax_tag_ids': [(6, 0, tax['tag_ids'])],
    #                 'partner_id': line.move_id.partner_id.id or line.partner_id.id,
    #                 'move_id': line.move_id.id,
    #                 'display_type': line.display_type,
    #             }): {
    #                 'name': tax['name'] + (' ' + _('(Discount)') if line.display_type == 'epd' else ''),
    #                 'balance': tax['amount'] / rate,
    #                 'amount_currency': tax['amount'],
    #                 'tax_base_amount': tax['base'] / rate * (-1 if line.tax_tag_invert else 1),
    #             }
    #             for tax in compute_all_currency['taxes']
    #             if tax['amount']
    #         }
    #         if not line.tax_repartition_line_id:
    #             line.compute_all_tax[frozendict({'id': line.id})] = {
    #                 'tax_tag_ids': [(6, 0, compute_all_currency['base_tags'])],
    #             }

    # def _convert_to_tax_base_line_dict(self):
    #     """ Convert the current record to a dictionary in order to use the generic taxes computation method
    #     defined on account.tax.
    #     :return: A python dictionary.
    #     """
    #     self.ensure_one()
    #     is_invoice = self.move_id.is_invoice(include_receipts=True)
    #     sign = -1 if self.move_id.is_inbound(include_receipts=True) else 1
    #     amount = self.amount_currency
    #     if self.amount_currency == 0.0:
    #         amount = self.line_price_reference * self.quantity
    #     price_unit = self.price_unit_with_discount
    #     return self.env['account.tax']._convert_to_tax_base_line_dict(
    #         self,
    #         partner=self.partner_id,
    #         currency=self.currency_id,
    #         product=self.product_id,
    #         taxes=self.tax_ids,
    #         price_unit=price_unit if is_invoice else self.amount_currency,
    #         quantity=self.quantity if is_invoice else 1.0,
    #         discount=self.discount if is_invoice else 0.0,
    #         account=self.account_id,
    #         analytic_distribution=self.analytic_distribution,
    #         price_subtotal=sign * amount,
    #         is_refund=self.is_refund,
    #         rate=(abs(amount) / abs(self.balance)) if self.balance else 1.0
    #     )