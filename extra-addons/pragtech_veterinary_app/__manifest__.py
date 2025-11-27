{
    'name': 'Odoo Veterinary Medical Management',
    'version': '17.0',
    'author': 'Pragmatic TechSoft Pvt Ltd.',
    "website": "http://pragtech.co.in",
    'depends': ['base', 'sale', 'purchase', 'account', 'sale_stock', 'stock', 'hr'],
    'summary': 'Odoo Medical Veterinary is used for Veterinary related service Odoo Veterinary Medical Management veterinary management system veterinary software veterinary app veterinary management software Veterinary Medical Management',
    'description': """
About Medical Veterinary
------------------------
Medical Veterinary is used for Veterinary related service.
<keywords>
Odoo Veterinary Medical Management
veterinary management system 
veterinary software
veterinary app
veterinary management software
Veterinary Medical Management
""",
    'category': 'Services',
    "data": [
        "pragtech_medical/security/medical_security.xml",
        "pragtech_medical/security/ir.model.access.csv",
        "pragtech_medical_pediatrics/security/ir.model.access.csv",
        'pragtech_medical/views/medical_view.xml',
        'pragtech_medical/views/res_users_view.xml',
        'pragtech_medical/wizard/appointment_wizard_view.xml',
        "pragtech_medical/data/medical_sequences.xml",
        "pragtech_medical/data/ethnic_groups.xml",
        "pragtech_medical/data/occupations.xml",
        "pragtech_medical/data/dose_units.xml",
        "pragtech_medical/data/HL7_drug_administration_routes.xml",
        "pragtech_medical/data/medicament_form.xml",
        "pragtech_medical/data/snomed_frequencies.xml",
        "pragtech_medical/data/medicament_categories.xml",
        "pragtech_medical/data/health_medicament_categories.xml",
        "pragtech_medical/data/WHO_list_of_essential_medicines.xml",
        "pragtech_medical/data/WHO_medicaments.xml",
        "pragtech_medical/data/medical_specialties.xml",
        "pragtech_medical/data/medicament_form.xml",
        "pragtech_medical/data/time_data.xml",
        "pragtech_medical/views/report_appointments.xml",
        "pragtech_medical/views/report_patient_medications.xml",
        "pragtech_medical/views/report_patient_vaccinations.xml",
        "pragtech_medical/views/report_patient_diseases.xml",
        'pragtech_medical/views/medical_report.xml',
        'pragtech_medical/views/report_prescription_main.xml',

        "pragtech_medical_genetics/views/medical_genetics_view.xml",
        "pragtech_medical_genetics/data/genetic_risks.xml",
        "pragtech_medical_genetics/security/ir.model.access.csv",

        "pragtech_medical_gyneco/views/medical_gyneco_view.xml",
        "pragtech_medical_gyneco/security/ir.model.access.csv",

        "pragtech_medical_inpatient/views/medical_inpatient_view.xml",
        "pragtech_medical_inpatient/data/medical_inpatient_sequence.xml",
        "pragtech_medical_inpatient/security/ir.model.access.csv",
        "pragtech_medical_inpatient/wizard/bed_transfer_wizard_view.xml",

        "pragtech_medical_nursing/views/medical_nursing_view.xml",
        'pragtech_medical_nursing/views/medical_nursing_sequence.xml',
        "pragtech_medical_nursing/security/ir.model.access.csv",

        "pragtech_medical_icu/views/medical_icu_view.xml",
        "pragtech_medical_icu/security/ir.model.access.csv",

        "pragtech_medical_imaging/views/medical_imaging_view.xml",
        'pragtech_medical_imaging/data/medical_imaging_data.xml',
        'pragtech_medical_imaging/views/medical_imaging_sequences.xml',
        'pragtech_medical_imaging/wizard/create_imaging_result.xml',
        'pragtech_medical_imaging/wizard/create_imaging_invoice.xml',
        'pragtech_medical_imaging/security/ir.model.access.csv',

        "pragtech_medical_lab/security/ir.model.access.csv",
        "pragtech_medical_lab/views/medical_lab_view.xml",
        "pragtech_medical_lab/data/medical_lab_sequences.xml",
        "pragtech_medical_lab/data/lab_test_data.xml",
        "pragtech_medical_lab/data/lab_test_data2.xml",
        "pragtech_medical_lab/wizard/wizard_multiple_test_request_view.xml",
        "pragtech_medical_lab/wizard/create_lab_test.xml",
        "pragtech_medical_lab/views/lab_test_report.xml",
        "pragtech_medical_lab/views/lab_result_report.xml",
        "pragtech_medical_lab/views/medical_view_report.xml",

        "pragtech_medical_invoice/wizard/evaluate_prescription_wizard_view.xml",
        "pragtech_medical_invoice/wizard/appointment_start_enddate_wizard_view.xml",
        "pragtech_medical_invoice/wizard/appoinment_speciality_search_wizard_view.xml",
        "pragtech_medical_invoice/wizard/appointment_invoice.xml",
        "pragtech_medical_invoice/wizard/prescription_invoice.xml",
        "pragtech_medical_invoice/wizard/create_lab_invoice.xml",
        "pragtech_medical_invoice/views/prescription_demo_report.xml",
        "pragtech_medical_invoice/views/prescription_report.xml",
        'pragtech_medical_invoice/views/report_prescription.xml',
        "pragtech_medical_invoice/views/medical_invoice_view.xml",

        "pragtech_medical_lifestyle/views/medical_lifestyle_view.xml",
        "pragtech_medical_lifestyle/data/recreational_drugs.xml",
        "pragtech_medical_lifestyle/security/ir.model.access.csv",

        "pragtech_medical_pediatrics/views/medical_pediatrics_view.xml",

        "pragtech_medical_service/views/medical_service_view.xml",
        'pragtech_medical_service/views/medical_service_sequence.xml',
        'pragtech_medical_service/wizard/medical_service_invoice_view.xml',
        'pragtech_medical_service/wizard/invoice_per_service_date_wizard_view.xml',
        'pragtech_medical_service/security/ir.model.access.csv',

        "pragtech_medical_surgery/views/medical_surgery_view.xml",
        "pragtech_medical_surgery/security/ir.model.access.csv",

        'pragtech_medical_archives/views/medical_archives_view.xml',
        'pragtech_medical_archives/security/ir.model.access.csv',
        "pragtech_medical_socioeconomics/views/medical_socioeconomics_view.xml",

        "pragtech_medical_stock/security/ir.model.access.csv",
        "pragtech_medical_stock/views/medical_stock_view.xml",
        "pragtech_medical_stock/wizard/prescription_shipment.xml",

        "pragtech_medical_veterinary/views/medical_veterinary_view.xml",
        "pragtech_medical_veterinary/wizard/wizard_multiple_test_request_vet_view.xml",
        "pragtech_medical_veterinary/data/veternary_diseases.xml",
        'pragtech_medical_veterinary/security/ir.model.access.csv',
    ],
    'images': ['images/Animated-veterinary-management.gif'],
    'live_test_url': 'http://www.pragtech.co.in/company/proposal-form.html?id=103&name=Veterinary-Medical',
    'currency': 'EUR',
    'price': 440,
    'license': 'OPL-1',
    'installable': True,
    'application': True,
    'auto_install': False,
}
