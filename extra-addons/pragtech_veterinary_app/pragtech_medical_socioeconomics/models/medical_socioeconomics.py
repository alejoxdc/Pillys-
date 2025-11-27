# coding=utf-8

#    Copyright (C) 2008-2010  Luis Falcon

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.


from odoo import api, fields, models, tools, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class occupation(models.Model):
    _name = "medical.occupation"
    _description = "Occupation / Job"

    name = fields.Char('Occupation', size=128)
    code = fields.Char('Code', size=64)


# Socioeconomics

class medical_patient(models.Model):
    _name = "medical.patient"
    _inherit = "medical.patient"

    ses = fields.Selection([
        ('0', 'Lower'),
        ('1', 'Lower-middle'),
        ('2', 'Middle'),
        ('3', 'Middle-upper'),
        ('4', 'Higher'),
    ], 'Socioeconomics', help="SES - Socioeconomic Status")

    education = fields.Selection([
        ('0', 'None'),
        ('1', 'Incomplete Primary School'),
        ('2', 'Primary School'),
        ('3', 'Incomplete Secondary School'),
        ('4', 'Secondary School'),
        ('5', 'University'),
    ], 'Education Level', help="Education Level")

    housing = fields.Selection([
        ('0', 'Shanty, deficient sanitary conditions'),
        ('1', 'Small, crowded but with good sanitary conditions'),
        ('2', 'Comfortable and good sanitary conditions'),
        ('3', 'Roomy and excellent sanitary conditions'),
        ('4', 'Luxury and excellent sanitary conditions'),
    ], 'Housing conditions', help="Housing and sanitary living conditions")

    hostile_area = fields.Boolean('Hostile Area',
                                  help="Check this box if the patient lives in a zone of high hostility (eg, war)")

    sewers = fields.Boolean('Sanitary Sewers', default=1)
    water = fields.Boolean('Running Water', default=1)
    trash = fields.Boolean('Trash recollection', default=1)
    electricity = fields.Boolean('Electrical supply', default=1)
    gas = fields.Boolean('Gas supply', default=1)
    telephone = fields.Boolean('Telephone', default=1)
    television = fields.Boolean('Television', default=1)
    internet = fields.Boolean('Internet')
    single_parent = fields.Boolean('Single parent family')
    domestic_violence = fields.Boolean('Domestic violence')
    working_children = fields.Boolean('Working children')
    teenage_pregnancy = fields.Boolean('Teenage pregnancy')
    sexual_abuse = fields.Boolean('Sexual abuse')
    drug_addiction = fields.Boolean('Drug addiction')
    school_withdrawal = fields.Boolean('School withdrawal')
    prison_past = fields.Boolean('Has been in prison', )
    prison_current = fields.Boolean('Is currently in prison')
    relative_in_prison = fields.Boolean('Relative in prison',
                                        help="Check if someone from the nuclear family - parents / sibblings  is or has been in prison")

    ses_notes = fields.Text("Extra info")

    fam_apgar_help = fields.Selection([
        ('1', 'Moderately'),
        ('2', 'Very much'),
    ], 'Help from family',
        help="Is the patient satisfied with the level of help coming from the family when there is a problem ?")

    fam_apgar_discussion = fields.Selection([
        ('1', 'Moderately'),
        ('2', 'Very much'),
    ], 'Family discussions on problems',
        help="Is the patient satisfied with the level talking over the problems as family ?")

    fam_apgar_decisions = fields.Selection([
        ('1', 'Moderately'),
        ('2', 'Very much'),
    ], 'Family decision making',
        help="Is the patient satisfied with the level of making important decisions as a group ?")

    fam_apgar_timesharing = fields.Selection([
        ('1', 'Moderately'),
        ('2', 'Very much'),
    ], 'Family time sharing', help="Is the patient satisfied with the level of time that they spend together ?")

    fam_apgar_affection = fields.Selection([
        ('1', 'Moderately'),
        ('2', 'Very much'),
    ], 'Family affection', help="Is the patient satisfied with the level of affection coming from the family ?")

    income = fields.Selection([
        ('h', 'High'),
        ('m', 'Medium / Average'),
        ('l', 'Low'),
    ], 'Income', index=True)
    fam_apgar_score = fields.Integer('Score', help="Total Family APGAR \n" \
                                                   "7 - 10 : Functional Family \n" \
                                                   "4 - 6  : Some level of disfunction \n" \
                                                   "0 - 3  : Severe disfunctional family \n")

    occupation = fields.Many2one('medical.occupation', 'Occupation')
    works_at_home = fields.Boolean('Works at home', help="Check if the patient works at his / her house")
    hours_outside = fields.Integer('Hours outside home',
                                   help="Number of hours a day the patient spend outside the house")

    @api.onchange('fam_apgar_help', 'fam_apgar_timesharing', 'fam_apgar_discussion', 'fam_apgar_decisions',
                  'fam_apgar_affection')
    def on_change_with_apgar_score(self):
        fam_apgar_help = self.fam_apgar_help or '0'
        fam_apgar_timesharing = self.fam_apgar_timesharing or '0'
        fam_apgar_discussion = self.fam_apgar_discussion or '0'
        fam_apgar_decisions = self.fam_apgar_decisions or '0'
        fam_apgar_affection = self.fam_apgar_affection or '0'
        v = {}
        apgar_score = int(fam_apgar_help) + int(fam_apgar_timesharing) + \
                      int(fam_apgar_decisions) + int(fam_apgar_discussion) + int(fam_apgar_affection)
        self.fam_apgar_score = apgar_score

        # return apgar_score

# medical_patient ()
