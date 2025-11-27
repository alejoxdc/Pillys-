# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class MedicalDiseaseGene (models.Model):
	_name = "medical.disease.gene"
	_description = "Genetic Risks"
	
	name = fields.Char('Official Symbol', size=16, index=True)
	long_name = fields.Char('Official Long Name', size=256, index=True)
	gene_id = fields.Char('Gene ID', size=8, help="default code from NCBI Entrez database.", index=True)
	chromosome = fields.Char('Affected Chromosome', size=2, help="Name of the affected chromosome", index=True)
	location = fields.Char('Location', size=32, help="Locus of the chromosome")
	dominance = fields.Selection([
		('d', 'dominant'),
		('r', 'recessive')], 'Dominance', index=True)
	info = fields.Text('Information', size=128, help="Name of the protein(s) affected")
	
	@api.model
	def name_search(self, name, args=None, operator='ilike', limit=100):
		args = args or []
		recs = self.browse()
		if name:
			recs = self.search([('long_name', '=', name)] + args, limit=limit)
		if not recs:
			recs = self.search([('name', operator, name)] + args, limit=limit)
		return recs.name_get()

	# @api.model
	# def name_search(self, name, args=None, operator='ilike', limit=100):
	# 	args = args or []
    #     recs = self.browse()
    #     args += [('name', operator, name)]
    #     args2 = [('long_name', operator, name)]
    #     recs = self.search(args, limit=limit)
	#
    #     recs = self.search(args2, limit=limit)
    #     return recs.name_get()


class MedicalGeneticRisk(models.Model):
	_name = 'medical.genetic.risk'
	_description = "Patient Genetic Risks"
	
	patient = fields.Many2one('medical.patient', 'Patient')
	disease_gene = fields.Many2one('medical.disease.gene', 'Disease Gene', required=True)


class MedicalFamilyDiseases (models.Model):
	_name = "medical.family.diseases"
	_description = "Family Diseases"
	
	patient = fields.Many2one('medical.patient', 'Patient', help="Patient Name")
	name = fields.Many2one('medical.pathology', 'Disease', required=True)
	xory = fields.Selection([
		('m', 'Maternal'),
		('f', 'Paternal')], 'Maternal or Paternal')
	relative = fields.Selection([
		('m', 'Mother'),
		('a', 'Father'),
		('b', 'Brother'),
		('s', 'Sister'),
		('au', 'Aunt'),
		('u', 'Uncle'),
		('ne', 'Nephew'),
		('ni', 'Niece'),
		('gf', 'Grandfather'),
		('gm', 'Grandmother'),
		('c', 'Cousin')], 'Relative', help="First degree = siblings, mother and father; second degree = Uncles, nephews and Nieces; third degree = Grandparents and cousins", index=True, required=True)


# Add to the Medical patient_data class (medical.patient) the genetic and family risks

class medical_patient (models.Model):
	_name = "medical.patient"
	_inherit = "medical.patient"
		
	genetic_risks = fields.Many2many('medical.genetic.risk', 'patient_genetic_risks_rel', 'patient_id', 'genetic_risk_id', 'Genetic Risks')
	family_history = fields.Many2many('medical.family.diseases', 'patient_familyhist_rel', 'patient_id', 'pathology_id', 'Family History')
	imaging_id = fields.Many2many('medical.imaging.test.request', 'pat_img_rel', 'patients', 'imgid')
