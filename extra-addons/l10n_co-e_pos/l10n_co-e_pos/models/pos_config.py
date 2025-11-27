# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _default_electronic_invoice_journal(self):
        return self.env['account.journal'].search([('type', '=', 'sale'), ('company_id', '=', self.env.company.id)],
                                                  limit=1)
    stop_invoice_print = fields.Boolean(string='Deshabilitar la impresión de PDF Factura electrónica', default=True) 
    electronic_invoice_journal_id = fields.Many2one(
        'account.journal', string='Diario de factura electrónica',
        domain=[('type', '=', 'sale')],
        help="Accounting journal used to create electronic invoices.",
        default=_default_electronic_invoice_journal)
    order_auto_invoice = fields.Boolean('Auto Facturar',  readonly=False)
    
    @api.constrains('company_id', 'electronic_invoice_journal_id')
    def _check_company_electronic_invoice_journal(self):
        for config in self:
            if config.electronic_invoice_journal_id \
                    and config.electronic_invoice_journal_id.company_id.id != config.company_id.id:
                raise ValidationError(
                    _("The electronic invoice journal and the point of sale %s must belong to its company.", config.name))

    @api.constrains('pricelist_id', 'use_pricelist', 'available_pricelist_ids', 'journal_id', 'invoice_journal_id',
                    'electronic_invoice_journal_id', 'payment_method_ids')
    def _check_currencies(self):
        super(PosConfig, self)._check_currencies()

        if self.electronic_invoice_journal_id.currency_id \
                and self.electronic_invoice_journal_id.currency_id.id != self.currency_id.id:
            raise ValidationError(
                _("The electronic invoice journal must be in the same currency as the Sales Journal or the company currency if that is not set."))


    def open_ui(self):
        for config in self:
            if not config.company_id.country_id:
                raise UserError(_("You have to set a country in your company setting."))
        return super().open_ui()


    partner_names_order = fields.Char(compute="_compute_partner_names_order")

    @api.depends()
    def _compute_partner_names_order(self):
        order = self.env["res.partner"]._get_names_order()
        for record in self:
            record.partner_names_order = order

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def _default_electronic_invoice_journal(self):
        return self.env['account.journal'].search([('type', '=', 'sale'), ('company_id', '=', self.env.company.id)],)
    stop_invoice_print = fields.Boolean(related='pos_config_id.stop_invoice_print', string='Deshabilitar la impresión de PDF Factura electrónica') 
    electronic_invoice_journal_id = fields.Many2one(related='pos_config_id.electronic_invoice_journal_id', string='Diario de factura electrónica',
        domain=[('type', '=', 'sale')], readonly=False, store=True,
        help="Accounting journal used to create electronic invoices.",
        default=_default_electronic_invoice_journal)
    order_auto_invoice = fields.Boolean(
        related='pos_config_id.order_auto_invoice',
        readonly=False)