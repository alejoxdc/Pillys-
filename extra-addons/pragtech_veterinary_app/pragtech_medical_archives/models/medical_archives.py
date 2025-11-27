# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _


class MedicalPaperArchive(models.Model):

    _description = 'Location of PAPER Patient Clinical History'
    _name = "medical.paper.archive"
    
    def get_patient_history(self):
        for patient_data in self:
            # print("PATIENT DATA !",patient_data,patient_data.name,patient_data.name.patient_id)
            patient_data.identification_code = patient_data.name.patient_id
        
    name = fields.Many2one('medical.patient', 'Patient ID', required=True,)
    location = fields.Many2one('medical.hospital.unit', 'Unit', required=True, help="Location / Unit where this clinical history document should reside.")
    current_location = fields.Many2one('medical.hospital.unit', 'Current Location', required=True, help="Location / Unit where this clinical history document should reside.")
    legacy = fields.Char('Legacy Code', size=64, help="If existing, please enter the old / legacy code associated to this Clinical History")
    requested_by = fields.Many2one('res.partner', 'Requested by', domain=[('is_person', '=', "1")], required=True, help="Person who last requested the document")
    request_date = fields.Datetime('Request Date')
    return_date = fields.Datetime('Returned Date')
    hc_status = fields.Selection([
        ('archived', 'Archived'),
        ('borrowed', 'Borrowed'),
        ('lost', 'Lost')], 'Status', required=True,)
    comments = fields.Text('Comments')
    identification_code = fields.Char(string='Code', compute='get_patient_history')
   
    _sql_constraints = [
                ('legacy_uniq', 'unique (legacy)', 'The History already exists !'),
                ('patient_uniq', 'UNIQUE(name)', 'The Patient History already exists !')]
