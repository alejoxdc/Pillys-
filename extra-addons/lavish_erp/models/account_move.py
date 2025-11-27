from email.policy import default
from odoo import models, fields,api , _
import json
import logging
from collections import defaultdict
from datetime import datetime

from odoo.exceptions import ValidationError
from odoo.tools import formatLang
import json
from odoo.tools.misc import format_date
from odoo.tools import get_lang
from odoo.exceptions import UserError

from datetime import timedelta
class GeneralLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'
    _description = 'General Ledger Custom Handler'

    def _get_query_amls(self, report, options, expanded_account_ids, offset=0, limit=None):
        """ Construct a query retrieving the account.move.lines when expanding a report line with or without the load
        more.
        :param options:               The report options.
        :param expanded_account_ids:  The account.account ids corresponding to consider. If None, match every account.
        :param offset:                The offset of the query (used by the load more).
        :param limit:                 The limit of the query (used by the load more).
        :return:                      (query, params)
        """
        additional_domain = [('account_id', 'in', expanded_account_ids)] if expanded_account_ids is not None else None
        queries = []
        all_params = []
        lang = self.env.user.lang or get_lang(self.env).code
        journal_name = f"COALESCE(journal.name->>'{lang}', journal.name->>'en_US')" if \
            self.pool['account.journal'].name.translate else 'journal.name'
        account_name = f"COALESCE(account.name->>'{lang}', account.name->>'en_US')" if \
            self.pool['account.account'].name.translate else 'account.name'
        for column_group_key, group_options in report._split_options_per_column_group(options).items():
            # Get sums for the account move lines.
            # period: [('date' <= options['date_to']), ('date', '>=', options['date_from'])]
            tables, where_clause, where_params = report._query_get(group_options, domain=additional_domain, date_scope='strict_range')
            ct_query = report._get_query_currency_table(group_options)
            query = f'''
                (SELECT
                    account_move_line.id,
                    account_move_line.date,
                    account_move_line.date_maturity,
                    account_move_line.name,
                    account_move_line.ref,
                    account_move_line.company_id,
                    account_move_line.account_id,
                    account_move_line.payment_id,
                    account_move_line.partner_id,
                    account_move_line.currency_id,
                    account_move_line.amount_currency,
                    account_move_line.date   AS invoice_date,
                    ROUND(account_move_line.debit * currency_table.rate, currency_table.precision)   AS debit,
                    ROUND(account_move_line.credit * currency_table.rate, currency_table.precision)  AS credit,
                    ROUND(account_move_line.balance * currency_table.rate, currency_table.precision) AS balance,
                    move.name                               AS move_name,
                    company.currency_id                     AS company_currency_id,
                    partner.name                            AS partner_name,
                    move.move_type                          AS move_type,
                    account.code                            AS account_code,
                    {account_name}                          AS account_name,
                    journal.code                            AS journal_code,
                    {journal_name}                          AS journal_name,
                    full_rec.id                             AS full_rec_name,
                    %s                                      AS column_group_key
                FROM {tables}
                JOIN account_move move                      ON move.id = account_move_line.move_id
                LEFT JOIN {ct_query}                        ON currency_table.company_id = account_move_line.company_id
                LEFT JOIN res_company company               ON company.id = account_move_line.company_id
                LEFT JOIN res_partner partner               ON partner.id = account_move_line.partner_id
                LEFT JOIN account_account account           ON account.id = account_move_line.account_id
                LEFT JOIN account_journal journal           ON journal.id = account_move_line.journal_id
                LEFT JOIN account_full_reconcile full_rec   ON full_rec.id = account_move_line.full_reconcile_id
                WHERE {where_clause}
                ORDER BY account_move_line.date, account_move_line.move_name, account_move_line.id)
            '''

            queries.append(query)
            all_params.append(column_group_key)
            all_params += where_params

        full_query = " UNION ALL ".join(queries)

        if offset:
            full_query += ' OFFSET %s '
            all_params.append(offset)
        if limit:
            full_query += ' LIMIT %s '
            all_params.append(limit)

        return (full_query, all_params)

class AccountMove(models.Model):
    _inherit = "account.move"
    
    resolution_number = fields.Char("Resolution number in invoice")
    resolution_date = fields.Date(string="Resolution Date")
    resolution_date_to = fields.Date(string="Resolution Date To")
    resolution_number_from = fields.Char(string="Resolution  Number From")
    resolution_number_to = fields.Char(string="Resolution Number To")

    def validate_number_phone(self, data):
        """
            Funcion que es utilizada en el reporte de factura para retornar la información de:
                ->	Telefono
                ->	Celular
        """
        if data.phone and data.mobile:
            return data.phone + " - " + data.mobile
        if data.phone and not data.mobile:
            return data.phone
        if data.mobile and not data.phone:
            return data.mobile

    def validate_state_city(self, data):
        """
            Funcion que es utilizada en el reporte de factura para retornar la información de:
                ->	Pais
                ->	Departamento
                ->	Ciudad
        """
        return (
            ((data.country_id.name + " ") if data.country_id.name else " ")
            + (" " + (data.state_id.name + " ") if data.state_id.name else " ")
            + (" " + data.city_id.name if data.city_id.name else "")
        )


    @api.model
    def create(self, vals):
        if not ("invoice_date" in vals) or not vals["invoice_date"]:
            vals["invoice_date"] = fields.Date.context_today(self)
        res = super(AccountMove, self).create(vals)
        return res

    def _post(self, soft=True):
        """
            Funcion que permite guardar los datos de la resolucion de la factura cuando esta es confirmada
        """
        result = super(AccountMove, self)._post(soft)
        for inv in self:
            sequence = self.env["ir.sequence.dian_resolution"].search(
                [
                    ("sequence_id", "=", self.journal_id.sequence_id.id),
                    ("active_resolution", "=", True),
                ],
                limit=1,
            )
            inv.resolution_number = sequence["resolution_number"]
            inv.resolution_date = sequence["date_from"]
            inv.resolution_date_to = sequence["date_to"]
            inv.resolution_number_from = sequence["number_from"]
            inv.resolution_number_to = sequence["number_to"]
        return result
class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

class TaxAdjustments(models.Model):
    _name = 'tax.adjustments.wizard'
    _description = 'Tax Adjustments Wizard'

    def _get_default_journal(self):
        return self.env['account.journal'].search([('type', '=', 'general')], limit=1).id

    reason = fields.Char(string='Justification')
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, default=_get_default_journal, domain=[('type', '=', 'general')])
    date_from = fields.Date(required=True, default=fields.Date.context_today)
    date_to = fields.Date(required=True, default=fields.Date.context_today)
    debit_account_id = fields.Many2one('account.account', string='Debit account', required=True,
                                       domain="[('deprecated', '=', False)]")
    credit_account_id = fields.Many2one('account.account', string='Credit account', required=True,
                                        domain="[('deprecated', '=', False)]")
    debit_account_id_2 = fields.Many2one('account.account', string='Debit account', required=True,
                                       domain="[('deprecated', '=', False)]")
    credit_account_id_2 = fields.Many2one('account.account', string='Credit account', required=True,
                                        domain="[('deprecated', '=', False)]")
    amount = fields.Monetary(currency_field='company_currency_id', compute="_amount_ret", string="Provision de retencion de renta", required=True)
    amount_2 = fields.Monetary(currency_field='company_currency_id', compute="_amount_ret", string="Provision de retencion de autorrenta",  required=True)
    company_currency_id = fields.Many2one('res.currency', readonly=True, default=lambda x: x.env.company.currency_id)
    amount_ingresos = fields.Float(compute="_amount_all")
    amount_gastos = fields.Float(compute="_amount_all")
    amount_retenciones = fields.Float(compute="_amount_all")
    amount_exe = fields.Float(string="(%) exento")
    amount_ret = fields.Float(string="(%) retencion de renta", default=35)
    amount_autorrenta = fields.Float(string="(%) autorrenta", default=0.455)
    move_id = fields.Many2one(
        "account.move", string="Journal Entry", ondelete="set null"
    )
    @api.depends('date_from','date_to','amount_ret','amount_autorrenta')
    def _amount_ret(self):
        for rec in self:
            rec.amount_2 = rec.amount_autorrenta * rec.amount_ingresos
            rec.amount = (rec.amount_ret/100) * (rec.amount_ingresos + rec.amount_gastos + rec.amount_retenciones)

    @api.depends('date_from','date_to','amount_ret','amount_autorrenta')
    def _amount_all(self):
        for rec in self:
            domain_ingresos = [
                ('move_id.state', '=', 'posted'),
                ('account_id.account_type', 'in', ['income', 'other_income']),
                ('date', '>=', rec.date_from),
                ('date', '<=', rec.date_to),
            ]
            domain_gastos = [
                ('move_id.state', '=', 'posted'),
                ('account_id.account_type', 'in', ['expense_direct_cost','expense','expense_depreciation']),
                ('date', '>=', rec.date_from),
                ('date', '<=', rec.date_to),
            ]
            domain_retencion = [
                ('move_id.state', '=', 'posted'),
                ('account_id.code', '=ilike', '135515'),
                ('date', '>=', rec.date_from),
                ('date', '<=', rec.date_to),
            ]

            ingresos_lines = self.env['account.move.line'].search(domain_ingresos)
            gastos_lines = self.env['account.move.line'].search(domain_gastos)
            retencion_lines = self.env['account.move.line'].search(domain_retencion)

            rec.amount_ingresos = sum(line.balance for line in ingresos_lines)
            rec.amount_gastos = sum(line.balance for line in gastos_lines)
            rec.amount_retenciones = sum(line.balance for line in retencion_lines)

    def create_move(self):
        move_line_vals = []

        # Vals for the amls corresponding to the ajustment tag
        move_line_vals.append((0, 0, {
            "partner_id": self.env.company.partner_id.id,
            'name': 'autorrenta' + str(self.date_to),
            'debit': abs(self.amount_2) or 0,
            'credit': 0,
            'account_id': self.debit_account_id.id,
        }))

        # Vals for the counterpart line
        move_line_vals.append((0, 0, {
            "partner_id": self.env.company.partner_id.id,
            'name': 'autorrenta' + str(self.date_to),
            'debit': 0,
            'credit': abs(self.amount_2) or 0,
            'account_id': self.credit_account_id.id,
        }))
        move_line_vals.append((0, 0, {
            "partner_id": self.env.company.partner_id.id,
            'name': 'Prov Renta' + str(self.date_to),
            'debit': abs(self.amount) or 0,
            'credit': 0,
            'account_id': self.debit_account_id_2.id,
        }))

        # Vals for the counterpart line
        move_line_vals.append((0, 0, {
            "partner_id": self.env.company.partner_id.id,
            'name': 'Prov Renta' + str(self.date_to),
            'debit': 0,
            'credit': abs(self.amount) or 0,
            'account_id': self.credit_account_id_2.id,
        }))
        # Create the move
        vals = {
            'journal_id': self.journal_id.id,
            'date': self.date_to,
            'line_ids': move_line_vals,
        }
        move = self.env['account.move'].create(vals)
        self.move_id = move.id
        move._post()




