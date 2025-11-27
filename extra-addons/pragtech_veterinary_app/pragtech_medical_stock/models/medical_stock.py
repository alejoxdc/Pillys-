# import base64
# import datetime
# import dateutil
# import email
# import json
# import lxml
# from lxml import etree
# import logging
# import pytz
# import re
# import socket
# import time
# import xmlrpclib
# from email.message import Message
# from email.utils import formataddr
# from werkzeug import url_encode
# from openerp import _, api, fields, models
# from openerp import exceptions
# from openerp import tools
# from openerp.addons.mail.models.mail_message import decode
# from openerp.tools.safe_eval import safe_eval as eval
# 
# from datetime import datetime, date
# from openerp.osv import fields, osv
# _logger = logging.getLogger(__name__)


from odoo import api, fields, models, tools, _
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class res_partner(models.Model):
    _name = 'res.partner'
    _inherit = "res.partner"

    def my_function(self):
        location_obj = self.env['stock.location']
        location_ids = location_obj.search([('usage', '=', 'inventory')])[0]
        for loc in location_obj.browse([location_ids]):
            var = loc.id
        return var

    warehouse = fields.Many2one('stock.location', 'Inventory', domain=[('usage', '=', 'inventory')],
                                default=my_function)


class medical_stock_rounding(models.Model):
    _name = "medical.patient.rounding"
    _inherit = "medical.patient.rounding"

    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], 'Status', default='draft')
    hospitalization_location = fields.Many2one('stock.location', 'Hospitalization Location')
    medicaments = fields.One2many('medical.patient.rounding.medicament', 'name', 'Medicaments')
    vaccines = fields.One2many('medical.patient.rounding.vaccine', 'name', 'Vaccines')
    moves = fields.One2many('stock.move', 'rounding', 'Stock Moves', readonly=True)
    medical_supplies = fields.One2many('medical.patient.ambulatory_care.medical_supply', 'name', 'Medical Supplies')

    def done_button(self):

        vaccination = self.env['medical.vaccination']
        mpr_obj = self.browse()

        lines_to_ship = {}
        medicaments_to_ship = []
        supplies_to_ship = []
        vaccines_to_ship = []
        patient_name = self.name.patient.id
        for medicament in self.medicaments:
            medicaments_to_ship.append(medicament)
        for medical_supply in self.medical_supplies:
            supplies_to_ship.append(medical_supply)
        for vaccine in self.vaccines:
            lot_number, expiration_date = '', ''
            if vaccine.lot:
                if vaccine.lot.name:
                    lot_number = vaccine.lot.name
                if vaccine.lot.expiration_date:
                    expiration_date = vaccine.lot.expiration_date

            vaccination_data = {
                'name': patient_name,
                'vaccine': vaccine.vaccine.id,
                'vaccine_lot': lot_number,
                'institution': '',
                'date': datetime.now(),
                'dose': vaccine.dose,
                'vaccine_expiration_date': expiration_date
            }
            vaccination.create(vaccination_data)
            vaccines_to_ship.append(vaccine)
        lines_to_ship['medicaments'] = medicaments_to_ship
        lines_to_ship['supplies'] = supplies_to_ship
        lines_to_ship['vaccines'] = vaccines_to_ship
        aa = self.create_stock_moves(self, lines_to_ship)

    def create_stock_moves(self, mpr, lines):
        move = self.env['stock.move']
        for var in mpr:
            for medicament in lines['medicaments']:
                move_info = {}
                move_info['product_id'] = medicament.medicament.name.id
                move_info['product_uom'] = medicament.medicament.name.uom_id.id
                move_info['product_uom_qty'] = medicament.quantity
                move_info['location_id'] = var.hospitalization_location.id  # var.name.patient.name.id + 1
                move_info[
                    'location_dest_id'] = 9  # var.name.patient.name.id #var.name.patient.name.customer_location.id
                move_info['price_unit'] = 1
                move_info['rounding'] = var.id
                move_info['name'] = medicament.medicament.name.id
                if medicament.lot:
                    if medicament.lot.expiration_date \
                            and medicament.lot.expiration_date < str(datetime.today().strftime('%Y-%m-%d')):
                        #                         raise  osv.except_osv(_('UserError'), _('Expired medicaments'))
                        raise UserError(_('Expired medicaments'))
                move_info['prodlot_id'] = medicament.lot.id
                if medicament.lot:
                    move_info['lot'] = medicament.lot.id
                new_move = move.create(move_info)
                new_move.write({
                    'state': 'done',
                    'date_expected': datetime.today().strftime('%Y-%m-%d'),
                })
            for medical_supply in lines['supplies']:
                move_info = {}
                move_info['product_id'] = medical_supply.product.id
                move_info['product_uom'] = medical_supply.product.product_tmpl_id.uom_id.id
                move_info['product_uom_qty'] = medical_supply.quantity
                move_info['location_id'] = var.hospitalization_location.id  # var.name.patient.name.id + 1
                move_info[
                    'location_dest_id'] = 9  # var.name.patient.name.id    var.name.patient.name.customer_location.id
                move_info['price_unit'] = 1
                move_info['rounding'] = var.id
                move_info['name'] = medical_supply.name.id
                if medical_supply.lot:
                    if medical_supply.lot.expiration_date \
                            and medical_supply.lot.expiration_date < str(date.today()):
                        #                             raise  osv.except_osv(_('UserError'), _('Expired supplies'))
                        raise UserError(_('Expired supplies'))

                move_info['prodlot_id'] = medical_supply.lot.id
                if medical_supply.lot:
                    move_info['lot'] = medical_supply.lot.id
                new_move = move.create(move_info)

                new_move.write({
                    'state': 'done',
                    'date_expected': date.today(),
                })

            for vaccine in lines['vaccines']:
                move_info = {}

                move_info['product_id'] = vaccine.vaccine.id
                move_info['product_uom'] = vaccine.vaccine.product_tmpl_id.uom_id.id
                move_info['product_uom_qty'] = vaccine.quantity
                move_info[
                    'location_id'] = var.hospitalization_location.id  # var.name.patient.name.id + 1
                move_info['location_dest_id'] = 9
                move_info['price_unit'] = 1
                move_info['rounding'] = var.id
                move_info['name'] = vaccine.vaccine.id
                if vaccine.lot:
                    if vaccine.lot.expiration_date \
                            and vaccine.lot.expiration_date < str(date.today()):
                        #                         raise  osv.except_osv(_('UserError'), _('Expired vaccines'))
                        raise UserError(_('Expired vaccines'))
                move_info['prodlot_id'] = vaccine.lot.id
                if vaccine.lot:
                    move_info['lot'] = vaccine.lot.id
                new_move = move.create(move_info)
                new_move.write({
                    'state': 'done',
                    'effective_date': date.today(),
                })
            if var.state == 'draft':
                var.write({'state': 'done'})

        return True


class medical_stock_ambulatory_care(models.Model):
    _name = "medical.patient.ambulatory_care"
    _inherit = "medical.patient.ambulatory_care"

    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], 'Status', readonly=True, default='draft')
    care_location = fields.Many2one('stock.location', 'Care Location')
    medicaments = fields.One2many('medical.patient.ambulatory_care.medicament', 'name', 'Medicaments')
    medical_supplies = fields.One2many('medical.patient.ambulatory_care.medical_supply', 'name', 'Medical Supplies')
    vaccines = fields.One2many('medical.patient.ambulatory_care.vaccine', 'name', 'Vaccines')
    moves = fields.One2many('stock.move', 'ambulatory_care', 'Stock Moves', readonly=True)

    def done_button(self):
        #         mpr_obj = self.pool.get('medical.patient.ambulatory_care').browse(cr,uid,ids,context={})
        vaccination = self.pool.get('medical.vaccination')
        lines_to_ship = {}
        medicaments_to_ship = []
        supplies_to_ship = []
        vaccines_to_ship = []

        patient_name = self.patient.id
        # patient_name = mpr.name.patient.id
        for medicament in self.medicaments:
            medicaments_to_ship.append(medicament)
        for medical_supply in self.medical_supplies:
            supplies_to_ship.append(medical_supply)
        for vaccine in self.vaccines:
            lot_number, expiration_date = '', ''
            if vaccine.lot:
                if vaccine.lot.name:
                    lot_number = vaccine.lot.name
                if vaccine.lot.expiration_date:
                    expiration_date = vaccine.lot.expiration_date

            vaccination_data = {
                'name': patient_name,
                'vaccine': vaccine.vaccine.id,
                'vaccine_lot': lot_number,
                'institution': '',
                'date': datetime.now(),
                'dose': vaccine.dose,
                'vaccine_expiration_date': expiration_date
            }

            vaccination.create(vaccination_data)
            vaccines_to_ship.append(vaccine)
        lines_to_ship['medicaments'] = medicaments_to_ship
        lines_to_ship['supplies'] = supplies_to_ship
        lines_to_ship['vaccines'] = vaccines_to_ship
        self.create_stock_moves(self, lines_to_ship)

    def create_stock_moves(self, mpr, lines):
        move = self.env['stock.move']
        for var in mpr:

            for medicament in lines['medicaments']:

                move_info = {}
                move_info['product_id'] = medicament.medicament.name.id
                move_info['product_uom'] = medicament.medicament.name.uom_id.id
                move_info['product_uom_qty'] = medicament.quantity
                move_info[
                    'location_id'] = var.care_location.id  # medicament.name.patient.name.id + 1
                move_info['location_dest_id'] = 9  # medicament.name.patient.name.id
                move_info['price_unit'] = 1
                move_info['ambulatory_care'] = var.id
                move_info['name'] = medicament.medicament.name.id
                if medicament.lot:
                    if medicament.lot.expiration_date \
                            and medicament.lot.expiration_date < str(date.today()):
                        #                         raise  osv.except_osv(_('UserError'), _('Expired medicaments'))
                        raise UserError(_('Expired medicaments'))
                move_info['prodlot_id'] = medicament.lot.id
                if medicament.lot:
                    move_info['lot'] = medicament.lot.id
                new_move = move.create(move_info)
                new_move.write({
                    'state': 'done',
                    'date_expected': date.today(),
                })
            for medical_supply in lines['supplies']:

                move_info = {}
                move_info['product_id'] = medical_supply.product.id
                move_info['product_uom'] = medical_supply.product.product_tmpl_id.uom_id.id
                move_info['product_uom_qty'] = medical_supply.quantity
                move_info['location_id'] = var.care_location.id  # medical_supply.name.patient.name.id + 1
                move_info['location_dest_id'] = 9
                move_info['price_unit'] = 1
                move_info['ambulatory_care'] = var.id
                move_info['name'] = medical_supply.name.id
                if medical_supply.lot:
                    if medical_supply.lot.expiration_date \
                            and medical_supply.lot.expiration_date < str(date.today()):
                        #                             raise  osv.except_osv(_('UserError'), _('Expired supplies'))
                        raise UserError(_('Expired supplies'))
                move_info['prodlot_id'] = medical_supply.lot.id
                if medical_supply.lot:
                    move_info['lot'] = medical_supply.lot.id
                new_move = move.create(move_info)

                new_move.write({
                    'state': 'done',
                    'date_expected': date.today(),
                })

            for vaccine in lines['vaccines']:
                move_info = {}

                move_info['product_id'] = vaccine.vaccine.id
                move_info['product_uom'] = vaccine.vaccine.product_tmpl_id.uom_id.id
                move_info['product_uom_qty'] = vaccine.quantity
                move_info['location_id'] = var.care_location.id  # vaccine.name.patient.name.id + 1
                move_info['location_dest_id'] = 9  # vaccine.name.patient.name.id
                move_info['price_unit'] = 1
                move_info['ambulatory_care'] = var.id
                move_info['name'] = vaccine.vaccine.id
                if vaccine.lot:
                    if vaccine.lot.expiration_date \
                            and vaccine.lot.expiration_date < str(date.today()):
                        #                         raise  osv.except_osv(_('UserError'), _('Expired vaccines'))
                        raise UserError(_('Expired vaccines'))
                move_info['prodlot_id'] = vaccine.lot.id
                if vaccine.lot:
                    move_info['lot'] = vaccine.lot.id
                new_move = move.create(move_info)
                new_move.write({
                    'state': 'done',
                    'effective_date': date.today(),
                })
            if var.state == 'draft':
                var.write({'state': 'done'})

        return True


class medical_patient_ambulatory_care_medicament(models.Model):
    _name = "medical.patient.ambulatory_care.medicament"
    _description = "Patient Ambulatory Care Medicament"

    name = fields.Many2one('medical.patient.ambulatory_care', 'Ambulatory ID')
    medicament = fields.Many2one('medical.medicament', 'Medicament', required=True)
    quantity = fields.Integer('Quantity', default=1)
    lot = fields.Many2one('stock.lot', 'Lot', required=True)
    short_comment = fields.Char('Comment',
                                help='Short comment on the specific drug')
    product = fields.Many2one('product.product', 'Product')


#     @api.onchange('medicament')
#     def on_change_medicament_ambulatory(self):
#         return {'value':{'product':self.medicament+1}}


class medical_patient_ambulatory_care_medical_supply(models.Model):
    _name = "medical.patient.ambulatory_care.medical_supply"
    _description = "Patient Ambulatory Care Medical Supply"

    name = fields.Many2one('medical.patient.ambulatory_care', 'Ambulatory ID')
    product = fields.Many2one('product.product', 'Medical Supply', required=True,
                              domain=[('is_medical_supply', '=', True)])
    short_comment = fields.Char('Comment',
                                help='Short comment on the specific drug')
    lot = fields.Many2one('stock.lot', 'Lot', required=True)
    quantity = fields.Integer('Quantity', default=1)


class medical_patient_ambulatory_care_vaccine(models.Model):
    _name = 'medical.patient.ambulatory_care.vaccine'
    _description = 'Patient Ambulatory Care Vaccine'

    name = fields.Many2one('medical.patient.ambulatory_care', 'Ambulatory ID')
    vaccine = fields.Many2one('product.product', 'Name', required=True, domain=[('is_vaccine', '=', True)])
    quantity = fields.Integer('Quantity', default=1)
    lot = fields.Many2one('stock.lot', 'Lot', required=True)
    dose = fields.Integer('Dose')
    next_dose_date = fields.Datetime('Next Dose')
    short_comment = fields.Char('Comment',
                                help='Short comment on the specific drug')


class medical_patient_rounding_medicament(models.Model):
    _name = "medical.patient.rounding.medicament"
    _description = "Patient Rounding Medicament"

    name = fields.Many2one('medical.patient.rounding', 'Ambulatory ID')
    medicament = fields.Many2one('medical.medicament', 'Medicament', required=True)
    quantity = fields.Integer('Quantity', default=1)
    lot = fields.Many2one('stock.lot', 'Lot', required=True)
    short_comment = fields.Char('Comment',
                                help='Short comment on the specific drug')
    product = fields.Many2one('product.product', 'Product')

    def on_change_medicament_rounding(self, cr, uid, ids, medicament):
        return {'value': {'product': medicament + 1}}


class medical_patient_rounding_medical_supply(models.Model):
    _name = "medical.patient.rounding.medical_supply"
    _description = "Patient Rounding Medical Supply"

    name = fields.Many2one('medical.patient.rounding', 'Ambulatory ID')
    product = fields.Many2one('product.product', 'Medical Supply', required=True,
                              domain=[('is_medical_supply', '=', True)])
    short_comment = fields.Char('Comment',
                                help='Short comment on the specific drug')
    lot = fields.Many2one('stock.lot', 'Lot', required=True)
    quantity = fields.Integer('Quantity', default=1)


class medical_patient_rounding_vaccine(models.Model):
    _name = 'medical.patient.rounding.vaccine'
    _description = 'Patient Rounding Vaccine'

    name = fields.Many2one('medical.patient.rounding', 'Ambulatory ID')
    vaccine = fields.Many2one('product.product', 'Name', required=True, domain=[('is_vaccine', '=', True)])
    quantity = fields.Integer('Quantity', default=1)
    lot = fields.Many2one('stock.lot', 'Lot', required=True)
    dose = fields.Integer('Dose')
    next_dose_date = fields.Datetime('Next Dose')
    short_comment = fields.Char('Comment',
                                help='Short comment on the specific drug')


class stock_move(models.Model):
    _name = 'stock.move'
    _inherit = "stock.move"

    ambulatory_care = fields.Many2one('medical.patient.ambulatory_care', 'Source Ambulatory Care')
    rounding = fields.Many2one('medical.patient.rounding', 'Source Rounding')
    lot = fields.Many2one('stock.lot', 'Lot')


class stock_production_lot(models.Model):
    _name = 'stock.lot'
    _inherit = "stock.lot"

    product_id = fields.Many2one('product.product', 'Product', required=True, domain=[('type', '<>', 'service')])
    expiration_date = fields.Date('Expiration Date', required=True)


class stock_picking(models.Model):
    _name = 'stock.picking'
    _inherit = 'stock.picking'

    prescription_order = fields.Many2one('medical.prescription.order', 'Source Prescription')
#     def create(self,cr,uid,vals,context = None):
#         picking_id = self.pool.get('stock.picking.type').search(cr,uid,[('name', '=', 'Delivery Orders')])
#         res = self.pool.get('stock.picking.type').browse(cr,uid,picking_id[0])
#         vals['picking_type_id'] = picking_id[0]
#         vals['location_id'] = res.default_location_src_id.id
#         vals['location_dest_id'] = res.default_location_dest_id.id
#         vals['company_id'] = 1
#         return super(stock_picking,self).create(cr,uid,vals,context)
