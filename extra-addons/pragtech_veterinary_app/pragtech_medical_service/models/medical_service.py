from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo import api, fields, models, tools, _


class medical_health_service(models.Model):
    _name = 'medical.health_service'
    _description = 'Health Service'

    name = fields.Char('ID', size=128, readonly=True)
    desc = fields.Char('Description', size=128, required=True)
    patient = fields.Many2one('medical.patient', 'Patient', required=True,)
    service_date = fields.Date('Date', required=True)
    service_line = fields.One2many('medical.health_service.line', 'name', 'Service Line', help="Service Line",
                                   )
    state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed'), ('invoiced', 'Invoiced'), ], 'State',
                             readonly=True, default='draft')
    inv_id = fields.Many2one('account.move', 'invoice', )

    _sql_constraints = [
        ('ref_uniq', 'unique (name)', 'The Service_ID must be unique')
    ]

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].get('medical.health_service')
        return super(medical_health_service, self).create(vals)

    def button_set_to_confirm(self):
        self.write({'state': 'confirmed'})
        return True


class medical_health_service_line(models.Model):
    _name = 'medical.health_service.line'
    _description = 'Health Service'

    name = fields.Many2one('medical.health_service', 'Service', readonly=True)
    desc = fields.Char('Description', size=256, required=True)
    appointment = fields.Many2one('medical.appointment', 'Appointment',
                                  help='Enter or select the date / ID of the appointment related to this evaluation')
    to_invoice = fields.Boolean('Invoice')
    product = fields.Many2one('product.product', 'Product', required=True)
    qty = fields.Integer('Qty', default=1)
    from_date = fields.Date('From')
    to_date = fields.Date('To')
