# -*- coding: utf-8 -*-
import datetime
from datetime import timedelta, date
import hashlib
import logging
import pyqrcode
import zipfile
import pytz
from unidecode import unidecode
from collections import defaultdict
from contextlib import contextmanager
from functools import lru_cache
from odoo import api, fields, models, Command, _
import base64
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
from lxml import etree
from io import BytesIO
from xml.sax import saxutils
import xml.etree.ElementTree as ET
_logger = logging.getLogger(__name__)
urllib3_logger = logging.getLogger('urllib3')
urllib3_logger.setLevel(logging.ERROR)
from . import global_functions
from pytz import timezone
from requests import post, exceptions
from lxml import etree
from odoo import models, fields, _, api
import logging
_logger = logging.getLogger(__name__)
import unicodedata
from odoo.tools.image import image_data_uri
import ssl
from odoo.tools import convert_file, html2plaintext, is_html_empty
ssl._create_default_https_context = ssl._create_unverified_context
DIAN = {'wsdl-hab': 'https://vpfe-hab.dian.gov.co/WcfDianCustomerServices.svc?wsdl',
        'wsdl': 'https://vpfe.dian.gov.co/WcfDianCustomerServices.svc?wsdl',
        'catalogo-hab': 'https://catalogo-vpfe-hab.dian.gov.co/Document/FindDocument?documentKey={}&partitionKey={}&emissionDate={}',
        'catalogo': 'https://catalogo-vpfe.dian.gov.co/Document/FindDocument?documentKey={}&partitionKey={}&emissionDate={}'}

TYPE_DOC_NAME = {
    'invoice': _('Invoice'),
    'credit': _('Credit Note'),
    'debit': _('Debit Note')
}

EDI_OPERATION_TYPE = [
    ('10', 'Estandar'),
    ('09', 'AIU'),
    ('11', 'Mandatos'),
   # ('20', 'Nota Crédito que referencia una factura electrónica'),
   # ('22', 'Nota Crédito sin referencia a facturas'),
   # ('30', 'Nota Débito que referencia una factura electrónica'),
   # ('32', 'Nota Débito sin referencia a facturas'),
]

EVENT_CODES = [
    ('02', '[02] Documento validado por la DIAN'),
    ('04', '[03] Documento rechazado por la DIAN'),
    ('030', '[030] Acuse de recibo'),
    ('031', '[031] Reclamo'),
    ('032', '[032] Recibo del bien'),
    ('033', '[033] Aceptación expresa'),
    ('034', '[034] Aceptación Tácita'),
    ('other', 'Otro')
]


class Invoice(models.Model):
    _inherit = "account.move"

          
    fecha_envio = fields.Datetime(string='Fecha de envío en UTC',copy=False)
    fecha_entrega = fields.Datetime(string='Fecha de entrega',copy=False)
    fecha_xml = fields.Datetime(string='Fecha de factura Publicada',copy=False)
    total_withholding_amount = fields.Float(string='Total de retenciones')
    invoice_trade_sample = fields.Boolean(string='Tiene muestras comerciales',)
    trade_sample_price = fields.Selection([('01', 'Valor comercial')],   string='Referencia a precio real',  )
    application_response_ids = fields.One2many('dian.application.response','move_id')
    get_status_event_status_code = fields.Selection([('00', 'Procesado Correctamente'),
                                                   ('66', 'NSU no encontrado'),
                                                   ('90', 'TrackId no encontrado'),
                                                   ('99', 'Validaciones contienen errores en campos mandatorios'),
                                                   ('other', 'Other')], string='StatusCode', default=False)
    get_status_event_response = fields.Text(string='Response')
    response_message_dian = fields.Text(string='Response Dian')
    response_eve_dian = fields.Text(string='Response Dian')
    message_error_DIAN_event = fields.Text(string='Response Dian error')
    titulo_state = fields.Selection([
        ('grey', 'No Titulo Valor'),
        ('red', 'Proceso'),
        ('green', 'Titulo Valor')], string='Titulo Valor', default='grey')

    fe_type = fields.Selection(
        [('01', 'Factura de venta'),
         ('02', 'Factura de exportación'),
         ('03', 'Documento electrónico de transmisión - tipo 03'),
         ('04', 'Factura electrónica de Venta - tipo 04'), 
         ],
        'Tipo De Factura Electronica',
        required=False,
        default='01',
        readonly=True,
    )
    fe_type_ei_ref = fields.Selection(
        [('01', 'Factura de venta'),
         ('02', 'Factura de exportación'),
        # ('03', 'Documento electrónico de transmisión - tipo 03'),
         #('04', 'Factura electrónica de Venta - tipo 04'),
         ('91', 'Nota Crédito'),
         ('92', 'Nota Débito'),
         ('96', 'Eventos (ApplicationResponse)'), ],
        'Tipo de Documento Electronico',
        required=False,
        readonly=True,
        compute='_type_ei_default',
        
    )
    fe_operation_type = fields.Selection(EDI_OPERATION_TYPE,
                                         'Tipo de Operacion',
                                         default='10',
                                         required=True)
    @api.depends('move_type','partner_id')
    def _type_ei_default(self):
        for rec in self:
            if rec.move_type in ('out_invoice','in_invoice') and not rec.is_debit_note:
                rec.fe_type_ei_ref = '01'
            elif rec.move_type in ('out_invoice','in_invoice') and rec.is_debit_note:
                rec.fe_type_ei_ref =  '92'
            elif rec.move_type in ('out_refund','in_refund'):
                rec.fe_type_ei_ref =  '91'  
            else:
                rec.fe_type_ei_ref =  '01'
    
    def validate_event(self):
        sql = """SELECT am.id 
                FROM account_move am
                WHERE am.titulo_state != 'green' 
                    AND am.move_type = 'out_invoice'
                    AND am.state = 'posted';"""
        self.env.cr.execute(sql)
        sql_result = self.env.cr.dictfetchall()

        # Crear lotes de 40 registros cada uno
        batch_size = 40
        for i in range(0, len(sql_result), batch_size):
            batch = sql_result[i:i + batch_size]
            inv_to_validate_dian = (
                self.env["account.move"].sudo().browse([n.get("id") for n in batch])
            )

            # Procesar cada registro en el lote
            for idian in inv_to_validate_dian:
                try:
                    # Creando un punto de guardado
                    with self.env.cr.savepoint():
                        idian.action_GetStatusevent()
                except Exception as e:
                    _logger.info(f"Error procesando el registro {idian.name}: {e}")


    def action_send_and_print(self):
        template = self.env.ref('l10n_co_e-invoice.email_template_edi_invoice_dian', raise_if_not_found=False)
        dian_constants = self.diancode_id._get_dian_constants(self)
        xml, name_xml = self.diancode_id.enviar_email_attached_document_xml(
            self.diancode_id.xml_response_dian,
            dian_document=self.diancode_id,
            dian_constants=dian_constants,
            data_header_doc=self,
        )
        zip_file_name = name_xml.split(".")[0]
        # Create a ZIP file containing XML and PDF files
        with BytesIO() as zip_buffer:
            with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED) as zip_file:
                # Ensure that xml is a bytes object before writing it to the ZIP file
                #xml_bytes = base64.b64decode().decode('utf-8')
                zip_file.writestr(name_xml, xml)

                pdf_file_name = zip_file_name + ".pdf"
                pdf_content = self.env['ir.actions.report'].sudo()._render_qweb_pdf("account.account_invoices", self.id)[0]
                zip_file.writestr(pdf_file_name, pdf_content)

            # Get the ZIP content as bytes
            zip_content = zip_buffer.getvalue()
        zip_base64 = base64.b64encode(zip_content).decode()
        dict_adjunto = {
            "res_id": self.id,
            "res_model": "account.move",
            "type": "binary",
            "name": zip_file_name + ".zip",
            "datas": zip_base64,
        }
        if template:
            template.sudo().attachment_ids = [(5, 0, [])]
            template.sudo().attachment_ids = [(0, 0, dict_adjunto)]
        # Encode the ZIP content in base64


        if any(not x.is_sale_document(include_receipts=True) for x in self):
            raise UserError(_("You can only send sales documents"))

        return {
            'name': _("Send"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.move.send',
            'target': 'new',
            'context': {
                'active_ids': self.ids,
                'default_mail_template_id': template and template.id or False,
            },
        }


    def action_invoice_sent_2(self):
        if self.company_id.production:
            for rec in self:
                dian_constants = rec.diancode_id._get_dian_constants(rec)
                xml, name_xml = rec.diancode_id.enviar_email_attached_document_xml(
                    rec.diancode_id.xml_response_dian,
                    dian_document=rec.diancode_id,
                    dian_constants=dian_constants,
                    data_header_doc=rec,
                )
                zip_file_name = name_xml.split(".")[0]
                # Create a ZIP file containing XML and PDF files
                with BytesIO() as zip_buffer:
                    with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED) as zip_file:
                        # Ensure that xml is a bytes object before writing it to the ZIP file
                        #xml_bytes = base64.b64decode().decode('utf-8')
                        zip_file.writestr(name_xml, xml)

                        pdf_file_name = zip_file_name + ".pdf"
                        pdf_content = self.env['ir.actions.report'].sudo()._render_qweb_pdf("account.account_invoices", rec.id)[0]
                        zip_file.writestr(pdf_file_name, pdf_content)

                    # Get the ZIP content as bytes
                    zip_content = zip_buffer.getvalue()

                # Encode the ZIP content in base64
                zip_base64 = base64.b64encode(zip_content).decode()

                template = self.env.ref('l10n_co_e-invoice.email_template_edi_invoice_dian', raise_if_not_found=False)
                lang = self.env.lang
                if template and template.lang:
                    lang = template._render_template(template.lang, 'account.move', rec.ids)
                compose_form = self.env.ref('account.account_invoice_send_wizard_form', raise_if_not_found=False)
                ctx = dict(
                    default_model='account.move',
                    default_res_id=rec.id,
                    default_res_model='account.move',
                    default_use_template=bool(template),
                    default_template_id=template and template.id or False,
                    default_composition_mode='comment',
                    mark_invoice_as_sent=True,
                    default_email_layout_xmlid="mail.mail_notification_layout_with_responsible_signature",
                    model_description=rec.with_context(lang=lang).type_name,
                    force_email=True,
                    active_ids=rec.ids,
                )

                dict_adjunto = {
                    "res_id": rec.id,
                    "res_model": "account.move",
                    "type": "binary",
                    "name": zip_file_name + ".zip",
                    "datas": zip_base64,
                }

                if template:
                    template.sudo().attachment_ids = [(5, 0, [])]
                    template.sudo().attachment_ids = [(0, 0, dict_adjunto)]

                return {
                    'name': _('Send Invoice'),
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'account.invoice.send',
                    'views': [(compose_form.id, 'form')],
                    'view_id': compose_form.id,
                    'target': 'new',
                    'context': ctx,
                }
        else:
            super(Invoice, self).action_invoice_sent()
   
   
    
    def dian_preview(self):
        for rec in self:
            if rec.cufe:
                return {
                    'type': 'ir.actions.act_url',
                    'target': 'new',
                    'url': 'https://catalogo-vpfe.dian.gov.co/document/searchqr?documentkey=' + rec.cufe,
                }

    def dian_pdf_view(self):
        for rec in self:
            if rec.cufe:
                return {
                    'type': 'ir.actions.act_url',
                    'target': 'new',
                    'url': 'https://catalogo-vpfe.dian.gov.co/Document/DownloadPDF?trackId=' + rec.cufe,
                }



    @api.depends('application_response_ids')
    def _compute_titulo_state(self):
        kanban_state = 'grey'
        for rec in self:
            for event in rec.application_response_ids:
                if event.response_code in ('034','033') and event.status == "exitoso":
                    kanban_state = 'green'
            rec.titulo_state = kanban_state

    def add_application_response(self):
        for rec in self:
            response_code = rec._context.get('response_code')
            ar = self.env['dian.application.response'].generate_from_electronic_invoice(rec.id, response_code)


    def _get_GetStatus_values(self):
        xml_soap_values = global_functions.get_xml_soap_values(
            self.company_id.certificate_file,
            self.company_id.certificate_key)
        cufe = self.cufe or self.ei_uuid
        if self.move_type == "in_invoice":
            cufe = self.cufe_cuds_other_system
        xml_soap_values['trackId'] = cufe
        return xml_soap_values

    def action_GetStatus(self):
        wsdl = DIAN['wsdl-hab']

        if self.company_id.production:
            wsdl = DIAN['wsdl']

        GetStatus_values = self._get_GetStatus_values()
        GetStatus_values['To'] = wsdl.replace('?wsdl', '')
        xml_soap_with_signature = global_functions.get_xml_soap_with_signature(
            global_functions.get_template_xml(GetStatus_values, 'GetStatus'),
            GetStatus_values['Id'],
            self.company_id.certificate_file,
            self.company_id.certificate_key)

        response = post(
            wsdl,
            headers={'content-type': 'application/soap+xml;charset=utf-8'},
            data=etree.tostring(xml_soap_with_signature, encoding="unicode"))

        if response.status_code == 200:
            self._get_status_response(response,send_mail=False)
        else:
            raise ValidationError(response.status_code)

        return True

    def action_GetStatusevent(self):
        wsdl = DIAN['wsdl-hab']

        if self.company_id.production:
            wsdl = DIAN['wsdl']

        GetStatus_values = self._get_GetStatus_values()
        GetStatus_values['To'] = wsdl.replace('?wsdl', '')
        xml_soap_with_signature = global_functions.get_xml_soap_with_signature(
            global_functions.get_template_xml(GetStatus_values, 'GetStatusEvent'),
            GetStatus_values['Id'],
            self.company_id.certificate_file,
            self.company_id.certificate_key)

        response = post(
            wsdl,
            headers={'content-type': 'application/soap+xml;charset=utf-8'},
            data=etree.tostring(xml_soap_with_signature, encoding="unicode"))

        if response.status_code == 200:
            self._get_status_response(response,send_mail=False)
        else:
            raise ValidationError(response.status_code)

        return True

    def create_records_from_xml(self):
        if not hasattr(self, 'message_error_DIAN_event') or not self.message_error_DIAN_event:
            return
        ar = self.env['dian.application.response']
        xml_string = self.message_error_DIAN_event  # Your XML string
        xml_bytes = xml_string.encode('utf-8')  # Convert to bytes
        root = etree.fromstring(xml_bytes)
        document_responses = []
        titulo_value = 'grey'
        for doc_response in root.findall('.//cac:DocumentResponse', namespaces=root.nsmap):
            if doc_response.find('.//cbc:ResponseCode', namespaces=root.nsmap).text in ['034', '033']:
                titulo_value = 'green'
            response_data = {
                'response_code': doc_response.find('.//cbc:ResponseCode', namespaces=root.nsmap).text,
                'name': doc_response.find('.//cbc:Description', namespaces=root.nsmap).text,
                'issue_date': doc_response.find('.//cbc:EffectiveDate', namespaces=root.nsmap).text,
                'move_id': self.id,
                'status': "exitoso",
                'dian_get': True,
                'response_message_dian': 'Procesado Correctamente',
            }
            doc_reference = doc_response.find('.//cac:DocumentReference', namespaces=root.nsmap)
            response_data['number'] = doc_reference.find('.//cbc:ID', namespaces=root.nsmap).text
            response_data['cude'] = doc_reference.find('.//cbc:UUID', namespaces=root.nsmap).text
            existing_record = ar.search([('cude', '=', response_data['cude'])], limit=1)
            if not existing_record:
                document_responses.append(response_data)
            else:
                continue 
        if document_responses or doc_response:
            if document_responses:
                ar.create(document_responses)
            self.titulo_state = titulo_value


    def _get_status_response(self, response, send_mail):
        b = "http://schemas.datacontract.org/2004/07/DianResponse"
        c = "http://schemas.microsoft.com/2003/10/Serialization/Arrays"
        s = "http://www.w3.org/2003/05/soap-envelope"
        strings = ''
        to_return = True
        status_code = 'other'
        root = etree.fromstring(response.content)
        date_invoice = self.invoice_date
        root2 = etree.tostring(root, pretty_print=True).decode()
        if not date_invoice:
            date_invoice = fields.Date.today()

        for element in root.iter("{%s}StatusCode" % b):
            if element.text in ('0', '00', '66', '90', '99'):
                # if element.text == '00':
                #     self.write({'state': 'exitoso'})

                    # if self.get_status_zip_status_code != '00':
                    #     if (self.move_type == "out_invoice"):
                    #         #self.company_id.out_invoice_sent += 1
                    #     elif (self.move_type == "out_refund" and self.document_type != "d"):
                    #         #self.company_id.out_refund_sent += 1
                    #     elif (self.move_type == "out_invoice" and self.document_type == "d"):
                    #         #self.company_id.out_refund_sent += 1

                status_code = element.text
        if status_code == '0':
            self.action_GetStatus()
            return True
        if status_code == '00':
            for element in root.iter("{%s}StatusMessage" % b):
                strings = element.text
            for element in root.iter("{%s}XmlBase64Bytes" % b):
                self.write({'message_error_DIAN_event': base64.b64decode(element.text).decode('utf-8') })
            #if not self.mail_sent:
            #    self.action_send_mail()
            to_return = True
        else:
            if send_mail:
                #self.send_failure_email()
            #self.send_failure_email()
                to_return = True
        for element in root.iter("{%s}string" % c):
            if strings == '':
                strings = '- ' + element.text
            else:
                strings += '\n\n- ' + element.text
        if strings == '':
            for element in root.iter("{%s}Body" % s):
                strings = etree.tostring(element, pretty_print=True)
            if strings == '':
                strings = etree.tostring(root, pretty_print=True)
        self.write({
            'get_status_event_status_code': status_code,
            'get_status_event_response': strings,
            'response_eve_dian' : strings})
        self.create_records_from_xml()
        return True

    @api.model
    def _get_time(self):
        fmt = "%H:%M:%S"
        now_utc = datetime.now(timezone("UTC"))
        now_time = now_utc.strftime(fmt)
        return now_time

    @api.model
    def _get_time_colombia(self):
        fmt = "%H:%M:%S-05:00"
        now_utc = datetime.datetime.now(timezone("UTC"))
        now_time = now_utc.strftime(fmt)
        return now_time

    def calcular_texto_descuento(self, id):

        if id == '00':
            return 'Descuento no condicionado'
        elif id == '01':
            return 'Descuento condicionado'
        else:
            return ''
    
    @staticmethod
    def _str_to_datetime(date):
        date = date.replace(tzinfo=pytz.timezone('UTC'))
        return date
    
    def generar_invoice_tax(self,document=None):
        contacto_compañia = self.company_id.partner_id.id
        invoice = self
        self.fecha_xml = datetime.datetime.combine(datetime.datetime.now(timezone("UTC")), datetime.datetime.now(
                pytz.timezone(str(self.user_id.partner_id.tz))).time()) - timedelta(hours=(datetime.datetime.now(
                pytz.timezone(str(self.user_id.partner_id.tz))).utcoffset().total_seconds() / 3600)) if self.user_id.partner_id.tz else datetime.datetime.combine(datetime.datetime.now(timezone("UTC")), datetime.datetime.now(pytz.timezone('America/Bogota')).time())-timedelta(hours=(datetime.datetime.now(pytz.timezone('America/Bogota')).utcoffset().total_seconds()/3600))
        if not self.fecha_entrega:
            self.fecha_entrega = datetime.datetime.combine(self.invoice_date, datetime.datetime.now().time())
        if not self.invoice_date_due:
            self._onchange_invoice_date()
            self._recompute_payment_terms_lines()

        create_date = self._str_to_datetime(self.fecha_xml)
        deliver_date = self._str_to_datetime(self.fecha_entrega)

        key_data = '{}{}{}'.format(invoice.company_id.software_identification_code, invoice.company_id.software_pin, invoice.name)
        sha384 = hashlib.sha384()
        sha384.update(key_data.encode())
        software_security_code = sha384.hexdigest()

        # reconciled_vals = self._get_reconciled_info_JSON_values()
        # invoice_prepaids = []
        # for reconciled_val in reconciled_vals:
        #     move_line_pago = self.env['account.move.line'].sudo().search([('id', '=', reconciled_val.get('payment_id'))])
        #     mapa_prepaid={
        #         'id': reconciled_val.get('payment_id'),
        #         'paid_amount': reconciled_val.get('amount'),
        #         'currency_id': str(self.currency_id.name),
        #         'received_date': str(move_line_pago.date),
        #         'paid_date': str(move_line_pago.date),
        #         'paid_time': '12:00:00'
        #     }
        #     invoice_prepaids.append(mapa_prepaid)

        invoice_lines = []

        tax_exclusive_amount = 0
        self.total_withholding_amount = 0.0
        tax_total_values = {}
        ret_total_values = {}
        # Bloque de código para imitar la estructura requerida por el XML de la DIAN para los totales externos
        # a las líneas de la factura.
        for line_id in self.invoice_line_ids.filtered(lambda line: line.display_type == 'product' and line.price_subtotal != 0):
            for tax in line_id.tax_ids:
                if tax.tributes == 'ZZ':
                    continue

                #Impuestos
                if '-' not in str(tax.amount) and tax.tributes != 'ZZ':
                    # Inicializa contador a cero para cada ID de impuesto
                    if tax.codigo_dian not in tax_total_values:
                        tax_total_values[tax.codigo_dian] = dict()
                        tax_total_values[tax.codigo_dian]['total'] = 0
                        tax_total_values[tax.codigo_dian]['info'] = dict()

                    # Suma al total de cada código, y añade información por cada tarifa.
                    if line_id.price_subtotal != 0:
                        price_subtotal_calc = line_id.price_subtotal
                    else:
                        taxes = False
                        if line_id.tax_line_id and line_id.tax_line_id != 'ZZ':
                            taxes = line_id.tax_line_id.compute_all(line_id.line_price_reference, line_id.currency_id, line_id.quantity,product=line_id.product_id,partner=self.partner_id)
                        price_subtotal_calc = taxes['total_excluded'] if taxes else line_id.quantity * line_id.line_price_reference

                    if tax.amount not in tax_total_values[tax.codigo_dian]['info']:
                        aux_total = tax_total_values[tax.codigo_dian]['total']
                        aux_total = aux_total + price_subtotal_calc * tax['amount'] / 100
                        aux_total = round(aux_total, 2)
                        tax_total_values[tax.codigo_dian]['total'] = aux_total
                        tax_total_values[tax.codigo_dian]['info'][tax.amount] = {
                            'taxable_amount': price_subtotal_calc,
                            'value': round(price_subtotal_calc * tax['amount'] / 100, 2), #round((line_id.quantity * tax['amount']) if tax.tax_type_id.code != '34' else ((line_id.quantity * tax['amount'] * line_id.product_id.drink_volume)/100), 2) if tax.amount_type == 'fixed' and line_id.product_id.drink_volume else round(price_subtotal_calc * tax['amount'] / 100, 2),
                            'technical_name': tax.nombre_dian,
                            'amount_type': tax.amount_type,
                            'per_unit_amount': tax['amount'],
                        }

                    else:
                        aux_tax = tax_total_values[tax.codigo_dian]['info'][tax.amount]['value']
                        aux_total = tax_total_values[tax.codigo_dian]['total']
                        aux_taxable = tax_total_values[tax.codigo_dian]['info'][tax.amount]['taxable_amount']
                        aux_tax = aux_tax + price_subtotal_calc * tax['amount'] / 100
                        aux_total = aux_total + price_subtotal_calc * tax['amount'] / 100
                        aux_taxable = aux_taxable + price_subtotal_calc
                        aux_tax = round(aux_tax, 2)
                        aux_total = round(aux_total, 2)
                        aux_taxable = round(aux_taxable, 2)
                        tax_total_values[tax.codigo_dian]['info'][tax.amount]['value'] = aux_tax
                        tax_total_values[tax.codigo_dian]['total'] = aux_total
                        tax_total_values[tax.codigo_dian]['info'][tax.amount]['taxable_amount'] = aux_taxable

                #retenciones
                else:
                    if tax.tributes != 'ZZ':
                        # Inicializa contador a cero para cada ID de impuesto
                        if line_id.price_subtotal != 0:
                            price_subtotal_calc = line_id.price_subtotal
                        else:
                            taxes = False
                            if line_id.tax_line_id and line_id.tax_line_id != 'ZZ':
                                taxes = line_id.tax_line_id.compute_all(line_id.line_price_reference, line_id.currency_id, line_id.quantity,product=line_id.product_id,partner=self.partner_id)
                            price_subtotal_calc = taxes['total_excluded'] if taxes else line_id.quantity * line_id.line_price_reference

                        if tax.codigo_dian not in ret_total_values:
                            ret_total_values[tax.codigo_dian] = dict()
                            ret_total_values[tax.codigo_dian]['total'] = 0
                            ret_total_values[tax.codigo_dian]['info'] = dict()

                        # Suma al total de cada código, y añade información por cada tarifa.
                        if abs(tax.amount) not in ret_total_values[tax.codigo_dian]['info']:
                            aux_total = ret_total_values[tax.codigo_dian]['total']
                            aux_total = aux_total + price_subtotal_calc * abs(tax['amount']) / 100
                            aux_total = round(aux_total, 2)
                            ret_total_values[tax.codigo_dian]['total'] = abs(aux_total)

                            ret_total_values[tax.codigo_dian]['info'][abs(tax.amount)] = {
                                'taxable_amount': abs(price_subtotal_calc),
                                'value': abs(round(price_subtotal_calc * tax['amount'] / 100, 2)),
                                'technical_name': tax.nombre_dian,
                                'amount_type': tax.amount_type,
                                'per_unit_amount': tax['amount'],
                            }

                        else:
                            aux_tax = ret_total_values[tax.codigo_dian]['info'][abs(tax.amount)]['value']
                            aux_total = ret_total_values[tax.codigo_dian]['total']
                            aux_taxable = ret_total_values[tax.codigo_dian]['info'][abs(tax.amount)]['taxable_amount']
                            aux_tax = aux_tax + price_subtotal_calc * abs(tax['amount']) / 100
                            aux_total = aux_total + price_subtotal_calc * abs(tax['amount']) / 100
                            aux_taxable = aux_taxable + price_subtotal_calc
                            aux_tax = round(aux_tax, 2)
                            aux_total = round(aux_total, 2)
                            aux_taxable = round(aux_taxable, 2)
                            ret_total_values[tax.codigo_dian]['info'][abs(tax.amount)]['value'] = abs(aux_tax)
                            ret_total_values[tax.codigo_dian]['total'] = abs(aux_total)
                            ret_total_values[tax.codigo_dian]['info'][abs(tax.amount)]['taxable_amount'] = abs(aux_taxable)

        for ret in ret_total_values.items():
            self.total_withholding_amount += abs(ret[1]['total'])

        contador = 1
        total_impuestos=0
        for index, invoice_line_id in enumerate(self.invoice_line_ids.filtered(lambda line: line.display_type == 'product' and line.price_subtotal != 0)):
            if invoice_line_id.price_unit>=0:
                if invoice_line_id.price_subtotal != 0:
                    price_subtotal_calc = invoice_line_id.price_subtotal
                else:
                    taxes = False
                    if invoice_line_id.tax_line_id and invoice_line_id.tax_line_id.tributes != 'ZZ':
                        taxes = invoice_line_id.tax_line_id.compute_all(invoice_line_id.line_price_reference, invoice_line_id.currency_id, invoice_line_id.quantity,product=invoice_line_id.product_id,partner=self.partner_id)
                    price_subtotal_calc = taxes['total_excluded'] if taxes else invoice_line_id.quantity * invoice_line_id.line_price_reference

                taxes = invoice_line_id.tax_ids
                tax_values = [price_subtotal_calc * tax['amount'] / 100 for tax in taxes]
                tax_values = [round(value, 2) for value in tax_values]
                tax_info = dict()
                ret_info = dict()

                for tax in invoice_line_id.tax_ids:
                    if '-' not in str(tax.amount) and tax.tributes != 'ZZ':
                        # Inicializa contador a cero para cada ID de impuesto
                        if tax.codigo_dian not in tax_info:
                            tax_info[tax.codigo_dian] = dict()
                            tax_info[tax.codigo_dian]['total'] = 0
                            tax_info[tax.codigo_dian]['info'] = dict()

                        # Suma al total de cada código, y añade información por cada tarifa para cada línea.
                        if invoice_line_id.price_subtotal != 0:
                            price_subtotal_calc = invoice_line_id.price_subtotal
                        else:
                            taxes = False
                            if invoice_line_id.tax_line_id:
                                taxes = invoice_line_id.tax_line_id.compute_all(invoice_line_id.line_price_reference, invoice_line_id.currency_id, invoice_line_id.quantity,product=invoice_line_id.product_id,partner=self.partner_id)
                            price_subtotal_calc = taxes['total_excluded'] if taxes else invoice_line_id.quantity * invoice_line_id.line_price_reference

                        total_impuestos += round(price_subtotal_calc * tax['amount'] / 100, 2)
                        if tax.amount not in tax_info[tax.codigo_dian]['info']:
                            aux_total = tax_info[tax.codigo_dian]['total']
                            aux_total = aux_total + price_subtotal_calc * tax['amount'] / 100
                            aux_total = round(aux_total, 2)
                            tax_info[tax.codigo_dian]['total'] = aux_total

                            tax_info[tax.codigo_dian]['info'][tax.amount] = {
                                'taxable_amount': price_subtotal_calc,
                                'value': round(price_subtotal_calc * tax['amount'] / 100, 2),
                                'technical_name': tax.nombre_dian,
                            }

                        else:
                            aux_tax = tax_info[tax.codigo_dian]['info'][tax.amount]['value']
                            aux_total = tax_info[tax.codigo_dian]['total']
                            aux_taxable = tax_info[tax.codigo_dian]['info'][tax.amount]['taxable_amount']
                            aux_tax = aux_tax + price_subtotal_calc * tax['amount'] / 100
                            aux_total = aux_total + price_subtotal_calc * tax['amount'] / 100
                            aux_taxable = aux_taxable + price_subtotal_calc
                            aux_tax = round(aux_tax, 2)
                            aux_total = round(aux_total, 2)
                            aux_taxable = round(aux_taxable, 2)
                            tax_info[tax.codigo_dian]['info'][tax.amount]['value'] = aux_tax
                            tax_info[tax.codigo_dian]['total'] = aux_total
                            tax_info[tax.codigo_dian]['info'][tax.amount]['taxable_amount'] = aux_taxable
                    else:
                        if tax.tributes == '06':
                            if tax.codigo_dian not in ret_info:
                                ret_info[tax.codigo_dian] = dict()
                                ret_info[tax.codigo_dian]['total'] = 0
                                ret_info[tax.codigo_dian]['info'] = dict()

                            # Suma al total de cada código, y añade información por cada tarifa para cada línea.
                            if invoice_line_id.price_subtotal != 0:
                                price_subtotal_calc = invoice_line_id.price_subtotal
                            else:
                                taxes = False
                                if invoice_line_id.tax_line_id:
                                    taxes = invoice_line_id.tax_line_id.compute_all(invoice_line_id.line_price_reference, invoice_line_id.currency_id, invoice_line_id.quantity,product=invoice_line_id.product_id,partner=self.partner_id)
                                price_subtotal_calc = taxes['total_excluded'] if taxes else invoice_line_id.quantity * invoice_line_id.line_price_reference

                        # total_impuestos += round(price_subtotal_calc * tax['amount'] / 100, 2)
                            if tax.amount not in ret_info[tax.codigo_dian]['info']:
                                aux_total = ret_info[tax.codigo_dian]['total']
                                aux_total = aux_total + price_subtotal_calc * tax['amount'] / 100
                                aux_total = round(aux_total, 2)
                                ret_info[tax.codigo_dian]['total'] = aux_total

                                ret_info[tax.codigo_dian]['info'][tax.amount] = {
                                    'taxable_amount': price_subtotal_calc,
                                    'value': round(price_subtotal_calc * tax['amount'] / 100, 2),
                                    'technical_name': tax.nombre_dian,
                                }

                            else:
                                aux_tax = ret_info[tax.codigo_dian]['info'][tax.amount]['value']
                                aux_total = ret_info[tax.codigo_dian]['total']
                                aux_taxable = ret_info[tax.codigo_dian]['info'][tax.amount]['taxable_amount']
                                aux_tax = aux_tax + price_subtotal_calc * tax['amount'] / 100
                                aux_total = aux_total + price_subtotal_calc * tax['amount'] / 100
                                aux_taxable = aux_taxable + price_subtotal_calc
                                aux_tax = round(aux_tax, 2)
                                aux_total = round(aux_total, 2)
                                aux_taxable = round(aux_taxable, 2)
                                ret_info[tax.codigo_dian]['info'][tax.amount]['value'] = aux_tax
                                ret_info[tax.codigo_dian]['total'] = aux_total
                                ret_info[tax.codigo_dian]['info'][tax.amount]['taxable_amount'] = aux_taxable

                if invoice_line_id.discount:
                    discount_line = invoice_line_id.price_unit * invoice_line_id.quantity * invoice_line_id.discount / 100
                    discount_line = round(discount_line, 2)
                    discount_percentage = invoice_line_id.discount
                    base_discount = invoice_line_id.price_unit * invoice_line_id.quantity
                else:
                    discount_line = 0
                    discount_percentage = 0
                    base_discount = 0

                if not invoice_line_id.product_id.enable_charges:
                    code = []
                    if invoice_line_id.product_id:
                        if invoice_line_id.move_id.fe_type == '02':
                            if not invoice_line_id.product_id.dian_customs_code:
                                raise UserError(_(
                                'Las facturas de exportación requieren un código aduanero en'
                                'todos los productos, completa esta información'
                                'antes de validar la factura.'
                                ))
                            code = [
                                invoice_line_id.product_id.dian_customs_code,
                                '020',
                                '195',
                                'Partida Arancelarias'
                            ]
                        if invoice_line_id.product_id.barcode:
                            code = [invoice_line_id.product_id.barcode, '010', '9', 'GTIN']
                        elif invoice_line_id.product_id.unspsc_code_id:
                            code = [invoice_line_id.product_id.unspsc_code_id.code, '001','10', 'UNSPSC']
                        elif invoice_line_id.product_id.default_code:
                            code = [invoice_line_id.product_id.default_code, '999', '', 'Estándar de adopción del contribuyente']
                        if not code:
                            code = ['NA', '999', '', 'Estándar de adopción del contribuyente']

                    mapa_line={
                        'id': index + contador,
                        'product_id': invoice_line_id.product_id,
                        'invoiced_quantity': invoice_line_id.quantity,
                        'uom_product_id': invoice_line_id.product_uom_id, # invoice_line_id.product_uom_id.codigo_fe_dian if invoice_line_id.product_uom_id else False,
                        'line_extension_amount': invoice_line_id.price_subtotal,
                        'item_description': saxutils.escape(invoice_line_id.name),
                        'price': (invoice_line_id.price_subtotal + discount_line)/ invoice_line_id.quantity,
                        'total_amount_tax': invoice.amount_tax,
                        'tax_info': tax_info,
                        'ret_info':ret_info,
                        'discount': discount_line,
                        'discount_percentage': discount_percentage,
                        'base_discount': base_discount,
                        'invoice_start_date': datetime.datetime.now().astimezone(pytz.timezone("America/Bogota")).strftime('%Y-%m-%d'),
                        'transmission_type_code': 1,
                        'transmission_description': 'Por operación',
                        'discount_text': self.calcular_texto_descuento(invoice_line_id.invoice_discount_text),
                        'discount_code': invoice_line_id.invoice_discount_text,
                        'multiplier_discount': discount_percentage,
                        'line_trade_sample_price': invoice_line_id.line_trade_sample_price,
                        'line_price_reference': (invoice_line_id.line_price_reference*invoice_line_id.quantity),
                        'brand_name': invoice_line_id.product_id.brand_id.name,
                        'model_name': invoice_line_id.product_id.model_id.name,
                        'StandardItemIdentificationID': code[0],
                        'StandardItemIdentificationschemeID': code[1],
                        'StandardItemIdentificationschemeAgencyID': code[2],
                        'StandardItemIdentificationschemeName': code[3]
                    }
                    #if invoice_line_id.move_id.usa_aiu and invoice_line_id.product_id and invoice_line_id.product_id.tipo_aiu:
                    #    mapa_line.update({'note': 'Contrato de servicios AIU por concepto de: ' + invoice_line_id.move_id.objeto_contrato})
                    invoice_lines.append(mapa_line)

                    taxs = 0
                    if invoice_line_id.tax_ids.ids:
                        for item in invoice_line_id.tax_ids:
                            if not item.amount < 0:
                                taxs += 1
                                # si existe tax para una linea, entonces el price_subtotal
                                # de la linea se incluye en tax_exclusive_amount
                                if taxs > 1:  # si hay mas de un impuesto no se incluye  a la suma del tax_exclusive_amount
                                    pass
                                else:
                                    if line_id.price_subtotal != 0:
                                        tax_exclusive_amount += invoice_line_id.price_subtotal
                                    else:
                                        taxes = False
                                        if invoice_line_id.tax_line_id and line_id.tax_line_id != 'ZZ':
                                            taxes = invoice_line_id.tax_line_id.compute_all(invoice_line_id.line_price_reference, invoice_line_id.currency_id, invoice_line_id.quantity,product=invoice_line_id.product_id,partner=self.partner_id)
                                        price_subtotal_calc = taxes['total_excluded'] if taxes else invoice_line_id.quantity * invoice_line_id.line_price_reference
                                        tax_exclusive_amount += (price_subtotal_calc)
            else:
                contador -= 1
            #fin for
            if invoice.partner_id and invoice.partner_id.firs_name:
                invoice_customer_first_name = invoice.partner_id.firs_name
            elif not invoice.partner_id and invoice.partner_id.parent_id.firs_name:
                invoice_customer_first_name = invoice.partner_id.parent_id.firs_name
            else:
                invoice_customer_first_name = ''
            if invoice.partner_id and invoice.partner_id.first_lastname:
                invoice_customer_family_name = invoice.partner_id.first_lastname
            elif not invoice.partner_id and invoice.partner_id.parent_id.first_lastname:
                invoice_customer_family_name = invoice.partner_id.parent_id.first_lastname
            else:
                invoice_customer_family_name = ''
            if invoice.partner_id and invoice.partner_id.second_lastname:
                invoice_customer_family_last_name = invoice.partner_id.second_lastname
            elif not invoice.partner_id and invoice.partner_id.parent_id.second_lastname:
                invoice_customer_family_last_name = invoice.partner_id.parent_id.second_lastname
            else:
                invoice_customer_family_last_name = ''
            if invoice.partner_id and invoice.partner_id.second_name:
                invoice_customer_middle_name = invoice.partner_id.second_name
            elif not invoice.partner_id and invoice.partner_id.parent_id.second_name:
                invoice_customer_middle_name = invoice.partner_id.parent_id.second_name
            else:
                invoice_customer_middle_name = ''
            if invoice.partner_id and invoice.partner_id.business_name:
                invoice_customer_commercial_registration = invoice.partner_id.business_name
            elif not invoice.partner_id and invoice.partner_id.parent_id.business_name:
                invoice_customer_commercial_registration = invoice.partner_id.parent_id.business_name
            else:
                invoice_customer_commercial_registration = 0
        cufe_cuds = ""
        cude_seed = ""
        qr = ""
        if self.move_type in ["out_invoice", "out_refund"]:
            cufe_cuds,qr,cude_seed,qr_code = self.calcular_cufe(tax_total_values, invoice.amount_untaxed, total_impuestos)
        if self.move_type in ["in_invoice", "in_refund"]:
            cufe_cuds,qr,cude_seed,qr_code = self.calcular_cuds(tax_total_values,invoice.amount_untaxed, total_impuestos)       
        tax_xml = self.generate_tax_xml(tax_total_values,self.currency_id.name)
        ret_xml = self.generate_ret_xml(ret_total_values,self.currency_id.name)
        line = self.create_invoice_lines(invoice_lines,self.currency_id.name)

        return {
                'cufe': cufe_cuds,
                'cude_seed': cude_seed,
                'qr':qr,
                'qr_code':qr_code,
                'tax_xml': tax_xml,
                'ret_xml': ret_xml,
                'ciuu_economic_activity_code': self.company_id.partner_id.ciiu_activity.code,
                'invoice_customer_first_name': invoice_customer_first_name,
                'invoice_customer_family_name': invoice_customer_family_name,
                'invoice_customer_family_last_name':invoice_customer_family_last_name,
                'invoice_customer_middle_name':invoice_customer_middle_name,
                'invoice_customer_phone': invoice.partner_id.phone,
                'invoice_issue_date': create_date.astimezone(pytz.timezone("America/Bogota")).strftime('%Y-%m-%d'),
                'invoice_issue_time': create_date.astimezone(pytz.timezone("America/Bogota")).strftime('%H:%M:%S-05:00'),
                'invoice_note':  self.remove_accents(html2plaintext(invoice.narration )) if not is_html_empty(invoice.narration ) else '',
                'invoice_delivery_date': deliver_date.astimezone(pytz.timezone('America/Bogota')).strftime('%Y-%m-%d'),
                'invoice_delivery_time': deliver_date.astimezone(pytz.timezone('America/Bogota')).strftime('%H:%M:%S'),
                'invoice_issue_date': create_date.astimezone(pytz.timezone("America/Bogota")).strftime('%Y-%m-%d'),
                'invoice_issue_time': create_date.astimezone(pytz.timezone("America/Bogota")).strftime('%H:%M:%S-05:00'),
                'software_security_code': software_security_code,
                'date_due': invoice.invoice_date_due,
                'invoice_customer_commercial_registration':invoice_customer_commercial_registration,
                #contact
                'ContactName': self.partner_contact_id.name,
                'ContactTelephone': self.partner_contact_id.phone or '',
                'ContactElectronicMail': self.partner_contact_id.email or '',
                
                'line': line,
                'line_extension_amount': '{:.2f}'.format(invoice.amount_untaxed  + invoice.invoice_discount),
                'tax_inclusive_amount': '{:.2f}'.format(invoice.amount_untaxed + total_impuestos + invoice.invoice_discount),
                'tax_exclusive_amount': '{:.2f}'.format(invoice.amount_untaxed ),
                'payable_amount': '{:.2f}'.format(invoice.amount_untaxed + total_impuestos), #invoice.amount_total + invoice.total_withholding_amount),
                #'payable_amount_discount': '{:.2f}'.format(invoice.amount_total + invoice.invoice_discount - invoice.invoice_charges_freight + invoice.total_withholding_amount),
            }
        
    def _generate_qr_code(self, silent_errors=False):
        self.ensure_one()
        if self.company_id.country_code == 'CO':
            payment_url = self.diancode_id.qr_data or self.cufe_seed
            barcode = self.env['ir.actions.report'].barcode(barcode_type="QR", value=payment_url, width=120, height=120)
            return image_data_uri(base64.b64encode(barcode))
        return super()._generate_qr_code(silent_errors)

    def calcular_cufe(self, tax_total_values,amount_untaxed,total_impuestos):
        rec_active_resolution = (self.journal_id.sequence_id.dian_resolution_ids.filtered(lambda r: r.active_resolution))
        create_date = self._str_to_datetime(self.fecha_xml)
        tax_computed_values = {tax: value['total'] for tax, value in tax_total_values.items()}

        numfac = self.name
        fecfac = create_date.astimezone(pytz.timezone('America/Bogota')).strftime('%Y-%m-%d')
        horfac = create_date.astimezone(pytz.timezone('America/Bogota')).strftime('%H:%M:%S-05:00')
        valfac = '{:.2f}'.format(amount_untaxed  + self.invoice_discount)
        codimp1 = '01'
        valimp1 = '{:.2f}'.format(tax_computed_values.get('01', 0))
        codimp2 = '04'
        valimp2 = '{:.2f}'.format(tax_computed_values.get('04', 0))
        codimp3 = '03'
        valimp3 = '{:.2f}'.format(tax_computed_values.get('03', 0))
        valtot = '{:.2f}'.format(amount_untaxed+total_impuestos)
        contacto_compañia = self.company_id.partner_id
        nitofe = str(contacto_compañia.vat_co)
        if self.company_id.production:
            tipoambiente = '1'
        else:
            tipoambiente = '2'
        numadq = str(self.partner_id.vat_co) or str(self.partner_id.parent_id.vat_co)
        if self.move_type == 'out_invoice' and not self.is_debit_note:
            citec =  rec_active_resolution.technical_key
        else:
            citec = self.company_id.software_pin

        total_otros_impuestos = sum([value for key, value in tax_computed_values.items() if key != '01'])
        iva = tax_computed_values.get('01', '0.00')
                #1
        cufe = unidecode(
            str(numfac) + str(fecfac) + str(horfac) + str(valfac) + str(codimp1) + str(valimp1) + str(codimp2) +
            str(valimp2) + str(codimp3) + str(valimp3) + str(valtot) + str(nitofe) + str(numadq) + str(citec) +
            str(tipoambiente))
        cufe_seed = cufe

        sha384 = hashlib.sha384()
        sha384.update(cufe.encode())
        cufe = sha384.hexdigest()

        qr_code = 'NumFac: {}\n' \
                  'FecFac: {}\n' \
                  'HorFac: {}\n' \
                  'NitFac: {}\n' \
                  'DocAdq: {}\n' \
                  'ValFac: {}\n' \
                  'ValIva: {}\n' \
                  'ValOtroIm: {:.2f}\n' \
                  'ValFacIm: {}\n' \
                  'CUFE: {}'.format(
                    numfac,
                    fecfac,
                    horfac,
                    nitofe,
                    numadq,
                    valfac,
                    iva,
                    total_otros_impuestos,
                    valtot,
                    cufe
                    )

        qr = pyqrcode.create(qr_code, error='L')        
        return cufe, qr.png_as_base64_str(scale=2),cufe_seed,qr_code

    def calcular_cuds(self, tax_total_values, amount_untaxed, total_impuestos):    
        create_date = self._str_to_datetime(self.fecha_xml)
        tax_computed_values = {tax: value['total'] for tax, value in tax_total_values.items()}
        numfac = self.name
        fecfac = create_date.astimezone(pytz.timezone('America/Bogota')).strftime('%Y-%m-%d')
        horfac = create_date.astimezone(pytz.timezone('America/Bogota')).strftime('%H:%M:%S-05:00')
        valfac = '{:.2f}'.format(amount_untaxed)
        codimp1 = '01'
        valimp1 = '{:.2f}'.format(tax_computed_values.get('01', 0))
        valtot = '{:.2f}'.format(amount_untaxed+total_impuestos) if self.move_type != 'entry' else '{:.2f}'.format(self.amount_total)
        company_contact = self.company_id.partner_id
        nitofe = str(company_contact.vat_co)
        if self.company_id.production:
            tipoambiente = '1'
        else:
            tipoambiente = '2'
        numadq = str(self.partner_id.vat_co) or str(self.partner_id.parent_id.vat_co)
        citec = self.company_id.software_pin

        total_otros_impuestos = sum([value for key, value in tax_computed_values.items() if key != '01'])
        iva = tax_computed_values.get('01', '0.00')

        cuds =  unidecode(
            str(numfac) + str(fecfac) + str(horfac) + str(valfac) + str(codimp1) + str(valimp1) + str(valtot) +
            str(numadq) + str(nitofe) + str(citec) + str(tipoambiente)
        )
        cuds_seed = cuds

        sha384 = hashlib.sha384()
        sha384.update(cuds.encode())
        cuds = sha384.hexdigest()

        if not self.company_id.production:
            qr_code = 'NumFac: {}\n' \
                    'FecFac: {}\n' \
                    'HorFac: {}\n' \
                    'NitFac: {}\n' \
                    'DocAdq: {}\n' \
                    'ValFac: {}\n' \
                    'ValIva: {}\n' \
                    'ValOtroIm: {:.2f}\n' \
                    'ValFacIm: {}\n' \
                    'CUDS: {}\n' \
                    'https://catalogo-vpfe-hab.dian.gov.co/document/searchqr?documentkey={}'.format(
                    numfac,
                    fecfac,
                    horfac,
                    nitofe,
                    numadq,
                    valfac,
                    iva,
                    total_otros_impuestos,
                    valtot,
                    cuds,
                    cuds
                    )
        else:
            qr_code = 'NumFac: {}\n' \
                  'FecFac: {}\n' \
                  'HorFac: {}\n' \
                  'NitFac: {}\n' \
                  'DocAdq: {}\n' \
                  'ValFac: {}\n' \
                  'ValIva: {}\n' \
                  'ValOtroIm: {:.2f}\n' \
                  'ValFacIm: {}\n' \
                  'CUDS: {}\n' \
                  'https://catalogo-vpfe.dian.gov.co/document/searchqr?documentkey={}'.format(
                    numfac,
                    fecfac,
                    horfac,
                    nitofe,
                    numadq,
                    valfac,
                    iva,
                    total_otros_impuestos,
                    valtot,
                    cuds,
                    cuds
                    )

        qr = pyqrcode.create(qr_code, error='L')

        return cuds, qr.png_as_base64_str(scale=2),cuds_seed,qr_code



    @api.model
    def generate_tax_xml(self, tax_total_values, currency_id):
        xml_content = ""

        for tax_id, data in tax_total_values.items():
            xml_content += "<cac:TaxTotal>\n"
            xml_content += f"   <cbc:TaxAmount currencyID=\"{currency_id}\">{data['total']}</cbc:TaxAmount>\n"
            xml_content += f"   <cbc:RoundingAmount currencyID=\"{currency_id}\">0</cbc:RoundingAmount>\n"
            
            for amount, info in data['info'].items():
                xml_content += "   <cac:TaxSubtotal>\n"
                xml_content += f"      <cbc:TaxableAmount currencyID=\"{currency_id}\">{info['taxable_amount']}</cbc:TaxableAmount>\n"
                xml_content += f"      <cbc:TaxAmount currencyID=\"{currency_id}\">{info['value']}</cbc:TaxAmount>\n"
                xml_content += "      <cac:TaxCategory>\n"
                xml_content += f"         <cbc:Percent>{'%.2f' % float(amount)}</cbc:Percent>\n"
                xml_content += "         <cac:TaxScheme>\n"
                xml_content += f"            <cbc:ID>{tax_id}</cbc:ID>\n"
                xml_content += f"            <cbc:Name>{info['technical_name']}</cbc:Name>\n"
                xml_content += "         </cac:TaxScheme>\n"
                xml_content += "      </cac:TaxCategory>\n"
                xml_content += "   </cac:TaxSubtotal>\n"
            
            xml_content += "</cac:TaxTotal>\n"

        return xml_content

    @api.model
    def generate_ret_xml(self, ret_total_values, currency_id):
        all_with_tax_totals = []

        if ret_total_values and self.move_type in ["out_invoice", "in_invoice"] and not self.is_debit_note:
            for tax_id, data in ret_total_values.items():
                # Crear un nuevo nodo WithholdingTaxTotal para cada tipo de impuesto
                with_tax_total = ET.Element('cac:WithholdingTaxTotal')
                ET.SubElement(with_tax_total, 'cbc:TaxAmount', {'currencyID': currency_id}).text = f'{data["total"]:.2f}'

                for amount, info in data['info'].items():
                    tax_subtotal = ET.SubElement(with_tax_total, 'cac:TaxSubtotal')
                    if tax_id == '06':
                        ET.SubElement(tax_subtotal, 'cbc:TaxableAmount', {'currencyID': currency_id}).text = '%0.2f' %  float(info['taxable_amount'])
                        ET.SubElement(tax_subtotal, 'cbc:TaxAmount', {'currencyID': currency_id}).text = '%0.2f' % float(info['value'])
                    else:
                        ET.SubElement(tax_subtotal, 'cbc:TaxableAmount', {'currencyID': currency_id}).text = '%0.3f' %  float(info['taxable_amount'])
                        ET.SubElement(tax_subtotal, 'cbc:TaxAmount', {'currencyID': currency_id}).text = '%0.3f' % float(info['value'])
                    tax_category = ET.SubElement(tax_subtotal, 'cac:TaxCategory')
                    if tax_id == '06':
                       ET.SubElement(tax_category, 'cbc:Percent').text = '%0.2f' % float(amount)
                    else:
                       ET.SubElement(tax_category, 'cbc:Percent').text = '%0.3f' % float(amount)

                    tax_scheme = ET.SubElement(tax_category, 'cac:TaxScheme')
                    ET.SubElement(tax_scheme, 'cbc:ID').text = str(tax_id)
                    ET.SubElement(tax_scheme, 'cbc:Name').text = str(info['technical_name'])

                # Convertir el nodo WithholdingTaxTotal a una cadena
                with_tax_total_str = ET.tostring(with_tax_total, encoding='utf-8', method='xml').decode('utf-8')
                all_with_tax_totals.append(with_tax_total_str)

        else:
            all_with_tax_totals.append(" ")

        # Unir todos los nodos WithholdingTaxTotal en una sola cadena
        return ''.join(all_with_tax_totals)
    
    @api.model
    def create_invoice_lines(self, invoice_lines, currency_id):
        invoice_lines_tags = []  # Lista para almacenar las etiquetas XML de cada línea de factura

        for invoice_line in invoice_lines:
            if (self.move_type == "out_invoice" and not self.is_debit_note)  or (self.move_type == "in_invoice" and not self.is_debit_note):
                invoice_line_tag = ET.Element('cac:InvoiceLine')
            if  self.is_debit_note:
                invoice_line_tag = ET.Element('cac:DebitNoteLine')
            if self.move_type == "out_refund" or self.move_type == "in_refund":
                invoice_line_tag = ET.Element('cac:CreditNoteLine')
            ET.SubElement(invoice_line_tag, 'cbc:ID').text = str(int(invoice_line.get('id', 0)))
            ET.SubElement(invoice_line_tag, 'cbc:Note').text = str(invoice_line.get('note', ''))
            if (self.move_type == "out_invoice" and not self.is_debit_note)  or (self.move_type == "in_invoice" and not self.is_debit_note):
                if invoice_line.get('uom_product_id') and invoice_line['uom_product_id'].dian_uom_id:
                    ET.SubElement(invoice_line_tag, 'cbc:InvoicedQuantity', {'unitCode': invoice_line['uom_product_id'].dian_uom_id.dian_code}).text = str(invoice_line['invoiced_quantity']) #{'unitCode': invoice_line['uom_product_id'].name}).text = str(invoice_line['invoiced_quantity'])
                else:
                    ET.SubElement(invoice_line_tag, 'cbc:InvoicedQuantity', {'unitCode': "EA"}).text = str(invoice_line['invoiced_quantity'])
            if self.is_debit_note:
                if invoice_line.get('uom_product_id') and invoice_line['uom_product_id'].dian_uom_id:
                    ET.SubElement(invoice_line_tag, 'cbc:DebitedQuantity', {'unitCode': invoice_line['uom_product_id'].dian_uom_id.dian_code}).text = str(invoice_line['invoiced_quantity']) #{'unitCode': invoice_line['uom_product_id'].name}).text = str(invoice_line['invoiced_quantity'])
                else:
                    ET.SubElement(invoice_line_tag, 'cbc:DebitedQuantity', {'unitCode': "EA"}).text = str(invoice_line['invoiced_quantity'])
            if self.move_type == "out_refund" or self.move_type == "in_refund":
                if invoice_line.get('uom_product_id') and invoice_line['uom_product_id'].dian_uom_id:
                    ET.SubElement(invoice_line_tag, 'cbc:CreditedQuantity', {'unitCode': invoice_line['uom_product_id'].dian_uom_id.dian_code}).text = str(invoice_line['invoiced_quantity']) #{'unitCode': invoice_line['uom_product_id'].name}).text = str(invoice_line['invoiced_quantity'])
                else:
                    ET.SubElement(invoice_line_tag, 'cbc:CreditedQuantity', {'unitCode': "EA"}).text = str(invoice_line['invoiced_quantity'])
            ET.SubElement(invoice_line_tag, 'cbc:LineExtensionAmount', {'currencyID': currency_id}).text = str(invoice_line['line_extension_amount'])
            if self.move_type == "in_invoice" and not self.is_debit_note:
                invoice_period = ET.SubElement(invoice_line_tag, "cac:InvoicePeriod")
                ET.SubElement(invoice_period, "cbc:StartDate").text = str(invoice_line['invoice_start_date'])
                ET.SubElement(invoice_period, "cbc:DescriptionCode").text = str(invoice_line['transmission_type_code'])
                ET.SubElement(invoice_period, "cbc:Description").text = str(invoice_line['transmission_description'])
            if invoice_line['line_extension_amount'] == 0:
                pricing_ref = ET.SubElement(invoice_line_tag, 'cac:PricingReference')
                alt_condition_price = ET.SubElement(pricing_ref, 'cac:AlternativeConditionPrice')
                ET.SubElement(alt_condition_price, 'cbc:PriceAmount', {'currencyID': currency_id}).text = str(invoice_line['line_price_reference'])
                ET.SubElement(alt_condition_price, 'cbc:PriceTypeCode').text = str(invoice_line['line_trade_sample_price'])

            if (self.move_type == "out_invoice" and not self.is_debit_note)  or (self.move_type == "in_invoice" and not self.is_debit_note):
                if float(invoice_line.get('line_extension_amount', 0)) > 0 and float(invoice_line.get('discount', 0)) > 0:
                    amount_base = float(invoice_line['line_extension_amount']) + float(invoice_line['discount'])
                    allowance_charge = ET.SubElement(invoice_line_tag, 'cac:AllowanceCharge')
                    ET.SubElement(allowance_charge, 'cbc:ID').text = '1'
                    ET.SubElement(allowance_charge, 'cbc:ChargeIndicator').text = 'false'
                    ET.SubElement(allowance_charge, 'cbc:AllowanceChargeReasonCode').text = invoice_line.get('discount_code')
                    ET.SubElement(allowance_charge, 'cbc:AllowanceChargeReason').text = invoice_line.get('discount_text')
                    ET.SubElement(allowance_charge, 'cbc:MultiplierFactorNumeric').text = str(invoice_line.get('discount_percentage'))
                    ET.SubElement(allowance_charge, 'cbc:Amount', {'currencyID': currency_id}).text = str(invoice_line.get('discount'))
                    ET.SubElement(allowance_charge, 'cbc:BaseAmount', {'currencyID': currency_id}).text = str(amount_base)

                for tax_id, data in invoice_line['tax_info'].items():
                    tax_total = ET.SubElement(invoice_line_tag, 'cac:TaxTotal')
                    ET.SubElement(tax_total, 'cbc:TaxAmount', {'currencyID': currency_id}).text = str(data['total'])
                    ET.SubElement(tax_total, 'cbc:RoundingAmount', {'currencyID': currency_id}).text = '0'
                    for amount, info in data['info'].items():
                        tax_subtotal = ET.SubElement(tax_total, 'cac:TaxSubtotal')
                        ET.SubElement(tax_subtotal, 'cbc:TaxableAmount', {'currencyID': currency_id}).text = str(info['taxable_amount'])
                        ET.SubElement(tax_subtotal, 'cbc:TaxAmount', {'currencyID': currency_id}).text = str(info['value'])
                        tax_category = ET.SubElement(tax_subtotal, 'cac:TaxCategory')
                        ET.SubElement(tax_category, 'cbc:Percent').text = '{:0.2f}'.format(float(amount))
                        tax_scheme = ET.SubElement(tax_category, 'cac:TaxScheme')
                        ET.SubElement(tax_scheme, 'cbc:ID').text = tax_id
                        ET.SubElement(tax_scheme, 'cbc:Name').text = info['technical_name']
        
            else:
                for tax_id, data in invoice_line['tax_info'].items():
                    tax_total = ET.SubElement(invoice_line_tag, 'cac:TaxTotal')
                    ET.SubElement(tax_total, 'cbc:TaxAmount', {'currencyID': currency_id}).text = str(data['total'])
                    ET.SubElement(tax_total, 'cbc:RoundingAmount', {'currencyID': currency_id}).text = '0'
                    for amount, info in data['info'].items():
                        tax_subtotal = ET.SubElement(tax_total, 'cac:TaxSubtotal')
                        ET.SubElement(tax_subtotal, 'cbc:TaxableAmount', {'currencyID': currency_id}).text = str(info['taxable_amount'])
                        ET.SubElement(tax_subtotal, 'cbc:TaxAmount', {'currencyID': currency_id}).text = str(info['value'])
                        tax_category = ET.SubElement(tax_subtotal, 'cac:TaxCategory')
                        ET.SubElement(tax_category, 'cbc:Percent').text = '{:0.2f}'.format(float(amount))
                        tax_scheme = ET.SubElement(tax_category, 'cac:TaxScheme')
                        ET.SubElement(tax_scheme, 'cbc:ID').text = tax_id
                        ET.SubElement(tax_scheme, 'cbc:Name').text = info['technical_name']
                if float(invoice_line.get('line_extension_amount', 0)) > 0 and float(invoice_line.get('discount', 0)) > 0:
                    amount_base = float(invoice_line['line_extension_amount']) + float(invoice_line['discount'])
                    allowance_charge = ET.SubElement(invoice_line_tag, 'cac:AllowanceCharge')
                    ET.SubElement(allowance_charge, 'cbc:ID').text = '1'
                    ET.SubElement(allowance_charge, 'cbc:ChargeIndicator').text = 'false'
                    ET.SubElement(allowance_charge, 'cbc:AllowanceChargeReasonCode').text = invoice_line.get('discount_code')
                    ET.SubElement(allowance_charge, 'cbc:AllowanceChargeReason').text = invoice_line.get('discount_text')
                    ET.SubElement(allowance_charge, 'cbc:MultiplierFactorNumeric').text = str(invoice_line.get('discount_percentage'))
                    ET.SubElement(allowance_charge, 'cbc:Amount', {'currencyID': currency_id}).text = str(invoice_line.get('discount'))
                    ET.SubElement(allowance_charge, 'cbc:BaseAmount', {'currencyID': currency_id}).text = str(amount_base)
                    
            item = ET.SubElement(invoice_line_tag, 'cac:Item')
            ET.SubElement(item, 'cbc:Description').text = invoice_line['item_description']
            SellersItemIdentification = ET.SubElement(item, 'cac:SellersItemIdentification')
            ET.SubElement(SellersItemIdentification, 'cbc:ID').text = str(invoice_line['product_id'].default_code)
            standard_item_identification = ET.SubElement(item, 'cac:StandardItemIdentification')
            if self.move_type == "out_invoice" or self.move_type == "out_refund":
                ET.SubElement(standard_item_identification, 'cbc:ID', {'schemeID': str(invoice_line['StandardItemIdentificationschemeID']), 'schemeAgencyID':str(invoice_line['StandardItemIdentificationschemeAgencyID']), 'schemeName':str(invoice_line['StandardItemIdentificationschemeName'])}).text = str(invoice_line['StandardItemIdentificationID'])
            if self.move_type == "in_invoice" or self.move_type == "in_refund":
                ET.SubElement(standard_item_identification, 'cbc:ID', {'schemeID': str(invoice_line['StandardItemIdentificationschemeID']), 'schemeAgencyID':str(invoice_line['StandardItemIdentificationschemeAgencyID']), 'schemeName':str(invoice_line['StandardItemIdentificationschemeName'])}).text = str(invoice_line['StandardItemIdentificationID'])

            price = ET.SubElement(invoice_line_tag, 'cac:Price')
            ET.SubElement(price, 'cbc:PriceAmount', {'currencyID': currency_id}).text = str(invoice_line['price'])
            if invoice_line.get('uom_product_id') and invoice_line['uom_product_id'].dian_uom_id:
                ET.SubElement(price, 'cbc:BaseQuantity', {'unitCode': invoice_line['uom_product_id'].dian_uom_id.dian_code}).text = str(invoice_line['invoiced_quantity'])
            else:
                ET.SubElement(price, 'cbc:BaseQuantity', {'unitCode': "EA"}).text = str(invoice_line['invoiced_quantity'])

            invoice_lines_tags.append(invoice_line_tag)  # Agregar la etiqueta de la línea a la lista

        #return invoice_lines_tags
        xml_str = [ET.tostring(tag, encoding='utf-8', method='xml') for tag in invoice_lines_tags]

        #_logger.info(xml_str)
        #xml_str = ET.tostring(invoice_lines_element, encoding='utf-8', method='xml')
        str_decoded = ''
        for byte_str in xml_str:
            str_decoded += byte_str.decode('utf-8')
            #_logger.info(str_decoded)
        return str_decoded

    def remove_accents(self, chain):
        s = ''.join((c for c in unicodedata.normalize('NFD', chain) if unicodedata.category(c) != 'Mn'))
        return s




class InvoiceLine(models.Model):
    _inherit = "account.move.line"
    line_price_reference = fields.Float(string='Precio de referencia')
    line_trade_sample_price = fields.Selection(string='Tipo precio de referencia',
                                               related='move_id.trade_sample_price')
    line_trade_sample = fields.Boolean(string='Muestra comercial', related='move_id.invoice_trade_sample')
    invoice_discount_text = fields.Selection(
        selection=[
            ('00', 'Descuento no condicionado'),
            ('01', 'Descuento condicionado')
        ],
        string='Motivo de Descuento',
    )
