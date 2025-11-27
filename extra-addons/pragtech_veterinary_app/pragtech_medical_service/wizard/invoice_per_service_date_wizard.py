from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo import api, fields, models, tools, _


class invoice_service_wizard(models.TransientModel):
    _name = 'invoice.service.wizard'
    _description = "This is form for view of tender"

    s_date = fields.Date('Start Date', )
    e_date = fields.Date('End Date', )

    def show_record(self):
        v = []
        rec = self.env['medical.health_service'].search([])
        obj = self.env['medical.health_service']
        if rec:
            if self.s_date and self.e_date:
                if (self.s_date <= rec.service_date and self.e_date >= rec.service_date):
                    v.append(rec.inv_id.id)
            elif self.s_date and not self.e_date:
                if (self.s_date == rec.service_date):
                    v.append(rec.inv_id.id)
            elif self.e_date and not self.s_date:
                if (self.e_date >= rec.service_date):
                    v.append(rec.inv_id.id)
            else:
                v.append(rec.inv_id.id)
        return {
            'name': _('Customer Invoices'),
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', v)],
        }
