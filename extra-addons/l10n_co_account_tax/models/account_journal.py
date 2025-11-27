# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2018 INNOVATECSA S.A.S (<http://www.innovatecsa.com>)
#
##############################################################################

from odoo import api, fields, models, _


class account_journal(models.Model):
    _inherit = "account.journal"

    taxes_ids = fields.Many2many('account.tax', 'account_journal_taxes_rel', 'journal_id', 'tax_id', 'Impuestos', domain=[('type_tax_use', '=', 'sale')])