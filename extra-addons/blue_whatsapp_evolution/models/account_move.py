# -*- coding: utf-8 -*-
#############################################################################
#
#    BlueConnect Solutions Ltda.
#
#    Copyright (C) 2024-TODAY BlueConnect Solutions (<https://www.conexaoazul.com>)
#    Author: Diego Santos (diego.blueconenct@gmail.com)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import models, fields, _
import json
import requests
import logging
import base64
import os
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    """Extends the account.move model to add WhatsApp messaging functionality."""
    _inherit = 'account.move'

    def get_invoice_pdf_report_attachment(self):
        """Obtiene el PDF de la factura como adjunto"""
        if len(self) < 2 and self.message_main_attachment_id:
            # Fallback a PDF ya adjunto
            pdf_content = self.message_main_attachment_id.raw
            pdf_name = self.message_main_attachment_id.name
            return pdf_content, pdf_name
            
        # Para múltiples facturas o sin adjunto, genera un PDF
        pdf_content = self.env['ir.actions.report']._render_qweb_pdf('account.account_invoices', self.ids)[0]
        pdf_name = self._get_invoice_report_filename() if len(self) == 1 else "Invoices.pdf"
        return pdf_content, pdf_name
    
    def _get_invoice_report_filename(self):
        """Devuelve un nombre de archivo apropiado para el PDF de la factura"""
        self.ensure_one()
        return f"{self.name.replace('/', '_')}.pdf" if self.name else "Invoice.pdf"

    def action_send_msg(self):
        """Este método es llamado cuando el usuario hace clic en el botón 'Enviar Mensaje WhatsApp'."""
        if not self.partner_id:
            raise UserError(_("Esta factura no tiene un contacto asociado."))
        
        attachment_id = False
        
        # Generar el PDF de la factura y crear un adjunto
        try:
            pdf_content, pdf_name = self.get_invoice_pdf_report_attachment()
            
            # Crear el adjunto para el PDF
            attachment_vals = {
                'name': pdf_name,
                'datas': base64.b64encode(pdf_content),
                'res_model': 'account.move',
                'res_id': self.id,
                'type': 'binary',
            }
            attachment = self.env['ir.attachment'].create(attachment_vals)
            attachment_id = attachment.id
        except Exception as e:
            _logger.error(f"Error al generar el PDF de la factura: {str(e)}")
        
        # Mensaje predeterminado que incluye información de la factura
        default_message = f"Estimado {self.partner_id.name},\n\nAdjunto encontrará información importante sobre su factura {self.name} por un monto de {self.amount_total} {self.currency_id.name}.\n\nGracias por su atención."
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Mensaje WhatsApp'),
            'res_model': 'whatsapp.send.message',
            'target': 'new',
            'view_mode': 'form',
            'view_type': 'form',
            'context': {
                'default_user_id': self.partner_id.id,
                'default_message': default_message,
                'default_attachments_ids': [(6, 0, [attachment_id])] if attachment_id else [],
                'default_move_id': self.id,
                'default_related_record_model': self._name,
                'default_related_record_id': self.id,
                'default_use_template': False,  # Cambiado de True a False
            },
        }

    def send_whatsapp_message(self, phone, text, url, headers):
        """Envía un mensaje a WhatsApp a través de la API y registra errores."""
        payload = json.dumps({
            "number": phone,
            "text": text
        })
        try:
            response = requests.post(url, headers=headers, data=payload)
            if response.status_code != 201:
                error_message = f"Fallo al enviar mensaje a WhatsApp: {response.text}"
                _logger.error(error_message)
                return False, error_message
            return True, response.text
        except Exception as e:
            error_message = f"Error al enviar mensaje a WhatsApp: {str(e)}"
            _logger.error(error_message)
            return False, error_message
