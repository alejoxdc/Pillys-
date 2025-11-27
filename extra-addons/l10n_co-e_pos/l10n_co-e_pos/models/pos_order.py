# -*- coding: utf-8 -*-
import logging
import psycopg2
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _
import logging
_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _export_for_ui(self, order):
        res = super()._export_for_ui(order)
        res.update({
            'pos_number': order.name, 
            })
        if order.account_move:
            res.update({
                'dian_number': order.account_move.name, 
                'dian_cufe': order.account_move.cufe, 
                'dian_co_qr_data': order.account_move.diancode_id.qr_data,
                'dian_ei_is_valid': order.account_move.journal_id.sequence_id.use_dian_control or False, 
                'dian_state_dian_document': order.account_move.state_dian_document, 
                'dian_resolution_number': order.account_move.resolution_number, 
                'dian_resolution_date': order.account_move.resolution_date, 
                'dian_resolution_date_to': order.account_move.resolution_date_to, 
                'dian_resolution_number_to': order.account_move.resolution_number_to, 
                'dian_resolution_number_from': order.account_move.resolution_number_from, 
                'dian_invoice_date': order.account_move.invoice_date, 
                'dian_invoice_date_due': order.account_move.invoice_date_due, 
                'dian_invoice_origin': order.account_move.invoice_origin, 
                'dian_ref': order.account_move.ref, 
                'dian_formatedNit': order.account_move.company_id.partner_id.vat, 
                'dian_company_idname': order.account_move.company_id.partner_id.name, 
                })
        return res

    def get_invoice(self):
        self.ensure_one()
        if self.account_move:
            vals = {
                "number": self.account_move.name,
                "cufe": self.account_move.cufe,
                "co_qr_data": self.account_move.diancode_id.qr_data,         
                "ei_is_valid" : self.account_move.journal_id.sequence_id.use_dian_control or False,
                "state_dian_document": self.account_move.state_dian_document,
                "resolution_number": self.account_move.resolution_number,
                "resolution_date": self.account_move.resolution_date,
                "resolution_date_to": self.account_move.resolution_date_to,
                "resolution_number_to": self.account_move.resolution_number_to,
                "resolution_number_from": self.account_move.resolution_number_from,
                "invoice_date": self.account_move.invoice_date,
                "invoice_date_due": self.account_move.invoice_date_due,
                "invoice_origin": self.account_move.invoice_origin,
                "ref": self.account_move.ref,
                "formatedNit": self.account_move.company_id.partner_id.vat,
                "company_idname": self.account_move.company_id.partner_id.name,
                'pos_number': self.name,
                }
        else:
            vals = {
                'pos_number': self.name,
            }
        return vals

    # def _prepare_invoice_vals(self):
    #     vals = super(PosOrder, self)._prepare_invoice_vals()
    #     vals['journal_id'] = self.session_id.config_id.electronic_invoice_journal_id.id
    #     return vals

    def _generate_pos_order_invoice(self):
        moves = self.env['account.move']

        for order in self:
            # Force company for all SUPERUSER_ID action
            if order.account_move:
                moves += order.account_move
                continue

            if not order.partner_id:
                raise UserError(_('Please provide a partner for the sale.'))

            move_vals = order._prepare_invoice_vals()
            new_move = order._create_invoice(move_vals)

            order.write({'account_move': new_move.id, 'state': 'invoiced'})
            new_move.sudo().with_company(order.company_id).with_context(skip_invoice_sync=True)._post()
            moves += new_move
            payment_moves = order._apply_invoice_payments(order.session_id.state == 'closed')
            new_move.sudo().with_company(order.company_id).with_context(skip_invoice_sync=True).validate_dian()
            # Send and Print
            #if self.env.context.get('generate_pdf', True):
            #    template = self.env.ref(new_move._get_mail_template())
            #    new_move.with_context(skip_invoice_sync=True)._generate_pdf_and_send_invoice(template)


            if order.session_id.state == 'closed':  # If the session isn't closed this isn't needed.
                # If a client requires the invoice later, we need to revers the amount from the closing entry, by making a new entry for that.
                order._create_misc_reversal_move(payment_moves)

        if not moves:
            return {}

        return {
            'name': _('Customer Invoice'),
            'view_mode': 'form',
            'view_id': self.env.ref('account.view_move_form').id,
            'res_model': 'account.move',
            'context': "{'move_type':'out_invoice'}",
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': moves and moves.ids[0] or False,
        }

    def apply_invoice_payments_co(self):
        self._apply_invoice_payments()

class PosOrderLineCustom(models.Model):
    _inherit = 'pos.order.line'

    price_list_id = fields.Many2one('product.pricelist', string='Price List')
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    qty = fields.Float(string='Quantity', default=1.0)
    amount_total = fields.Monetary(string='Total', compute='_compute_amount_total', store=True)

    @api.depends('qty', 'price_unit')
    def _compute_amount_total(self):
        for line in self:
            line.amount_total = line.price_unit * line.qty

    def _export_for_ui(self, orderline):
        res = super()._export_for_ui(orderline)
        res.update({
            'default_code': orderline.product_id.default_code,
            })
        return res

class PosSession(models.Model):
    _inherit = "pos.session"

    def _loader_params_account_journal(self):
        return {
            "search_params": {
                "domain": [("id", "=", self.config_id.electronic_invoice_journal_id.id)],
                "fields": [
                    "name",
                ],
            }
        }

    def _get_pos_ui_account_journal(self, params):
        return self.env["account.journal"].search_read(**params["search_params"])

    def _loader_params_res_partner(self):
        res = super()._loader_params_res_partner()
        if self.company_id.country_code == 'CO':
            res["search_params"]["fields"].extend(["firs_name", "l10n_latam_identification_type_id", "second_name", "first_lastname","second_lastname","is_company","city_id", 'country_code', 'category_id', 'fiscal_responsability_ids','tribute_id'])
        return res

    def _is_co_company(self):
        return self.company_id.country_code == "CO"

    def _pos_ui_models_to_load(self):
        res = super()._pos_ui_models_to_load()
        if self._is_co_company():
            res.extend(["l10n_latam.identification.type",  "res.city", "account.journal",'res.partner.category','dian.tributes','dian.fiscal.responsability'])
        return res

    def _get_pos_ui_res_city(self, params):
        return self.env["res.city"].search_read(**params["search_params"])

    def _loader_params_res_city(self):
        return {"search_params": {"domain": [("country_id.code", "=", "CO")], "fields": ["name", "country_id", "state_id"]}}

    def _get_pos_ui_l10n_latam_identification_type(self, params):
        return self.env["l10n_latam.identification.type"].search_read(**params["search_params"])

    def _loader_params_l10n_latam_identification_type(self):
        """filter only identification types used in Peru"""
        return {
            "search_params": {
                "domain": [
                    ("l10n_co_document_code", "!=", False),
                    ("active", "=", True),
                ],
                "fields": ["name"],
            },
        }

    def _loader_params_res_partner_category(self):
        return {
            'search_params': {
                'domain': [],
                'fields': ['id', 'name'],
            },
        }

    def _get_pos_ui_res_partner_category(self, params):
        return self.env['res.partner.category'].search_read(**params['search_params'])


    def _loader_params_dian_tributes(self):
        return {
            'search_params': {
                'domain': [],
                'fields': ['id', 'name'],
            },
        }
        
    def _get_pos_ui_dian_tributes(self, params):
        return self.env['dian.tributes'].search_read(**params['search_params'])


    def _loader_params_dian_fiscal_responsability(self):
        return {
            'search_params': {
                'domain': [],
                'fields': ['id', 'name'],
            },
        }
    def _get_pos_ui_dian_fiscal_responsability(self, params):
        return self.env['dian.fiscal.responsability'].search_read(**params['search_params'])


class AccountMove(models.Model):
    _inherit = 'account.move'

    pos_order_ids = fields.One2many('pos.order', 'account_move')
    pos_payment_ids = fields.One2many('pos.payment', 'account_move_id')
    pos_refunded_invoice_ids = fields.Many2many('account.move', 'refunded_invoices', 'refund_account_move', 'original_account_move')
    pos_session_id = fields.Many2one('pos.session', string='POS Session', compute='_compute_pos_session')

    def _compute_pos_order_count(self):
        for move in self:
            move.pos_order_count = len(move.pos_order_ids)

    def _compute_pos_payment_count(self):
        for move in self:
            move.pos_payment_count = len(move.pos_payment_ids)

    def _compute_pos_refunded_invoice_count(self):
        for move in self:
            move.pos_refunded_invoice_count =  len(move.pos_order_ids.refunded_order_ids)

    def _compute_pos_session(self):
        for move in self:
            pos_order = move.pos_order_ids and move.pos_order_ids[0] or False
            move.pos_session_id = pos_order and pos_order.session_id or False

    pos_order_count = fields.Integer(string='POS Orders', compute='_compute_pos_order_count')
    pos_payment_count = fields.Integer(string='POS Payments', compute='_compute_pos_payment_count')
    pos_refunded_invoice_count = fields.Integer(string='Refunded Invoices', compute='_compute_pos_refunded_invoice_count')

    def action_view_pos_orders(self):
        self.ensure_one()
        return {
            'name': 'POS Orders',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'pos.order',
            'domain': [('id', 'in', self.pos_order_ids.ids)],
            'context': {'create': False},
        }

    def action_view_pos_payments(self):
        self.ensure_one()
        return {
            'name': 'POS Payments',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'pos.payment',
            'domain': [('id', 'in', self.pos_payment_ids.ids)],
            'context': {'create': False},
        }

    def action_view_refunded_invoices(self):
        self.ensure_one()
        return {
            'name': 'Refunded Invoices',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('id', 'in', self.pos_order_ids.refunded_order_ids.ids)],
            'context': {'create': False},
        }

    def action_view_pos_session(self):
        self.ensure_one()
        if self.pos_session_id:
            return {
                'name': 'POS Session',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'pos.session',
                'res_id': self.pos_session_id.id,
                'target': 'current',
                'context': {'create': False},
            }
        return {}

