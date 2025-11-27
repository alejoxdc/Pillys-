from odoo import api, fields, models, tools, _
from datetime import datetime
from babel.dates import format_date
import logging

_logger = logging.getLogger(__name__)


class AppointmentWizard(models.TransientModel):
    _name = 'appointment.wizard'
    _description = "This is form for view of Appointment"
    
    phy_id = fields.Many2one("medical.physician", 'Name Of Physician')
    a_date = fields.Date('Appointment Date')
    
    def show_record(self):
        v = []
        self.ensure_one()
        for rec in self:
            apt_ids = self.env['medical.appointment'].search([('doctor', '=', rec.phy_id.id), ('state', '=', 'confirmed')])
            _logger.info("Physician Record ID is --> {}".format(rec.phy_id.id))
            date_convert = rec.a_date
            for apt in apt_ids:
                b_day = datetime.strptime(str(apt.appointment_sdate), '%Y-%m-%d %H:%M:%S')
                formatted_date = date_convert.strftime("%Y-%m-%d")
                _logger.info("FORMATTED DATE IS ---> {}".format(formatted_date))
                _logger.info("Dates to comapre are ---> {} {}".format(str(b_day.date()), formatted_date))
                if ((str(b_day.date())== formatted_date)):
                    _logger.info("COMPARISON MATCHED")
                    v.append(apt.id)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Appointments',
            'res_model': 'medical.appointment',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', v)]
        }
