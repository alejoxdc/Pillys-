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
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    """Extends the sale.order model to add WhatsApp messaging functionality."""
    _inherit = 'sale.order'

    def get_sale_pdf_report_attachment(self):
        """Obtiene el PDF del presupuesto/pedido de venta como adjunto"""
        # Para múltiples pedidos o sin adjunto, genera un PDF
        pdf_content = self.env['ir.actions.report']._render_qweb_pdf('sale.action_report_saleorder', self.ids)[0]
        pdf_name = f"{self.name.replace('/', '_')}.pdf" if len(self) == 1 else "SalesOrders.pdf"
        return pdf_content, pdf_name

    def action_send_msg(self):
        """Este método es llamado cuando el usuario hace clic en el botón 'Enviar Mensaje WhatsApp'."""
        if not self.partner_id:
            raise UserError(_("Este pedido no tiene un contacto asociado."))
        
        attachment_id = False
        
        # Generar el PDF del pedido y crear un adjunto
        try:
            pdf_content, pdf_name = self.get_sale_pdf_report_attachment()
            
            # Crear el adjunto para el PDF
            attachment_vals = {
                'name': pdf_name,
                'datas': base64.b64encode(pdf_content),
                'res_model': 'sale.order',
                'res_id': self.id,
                'type': 'binary',
            }
            attachment = self.env['ir.attachment'].create(attachment_vals)
            attachment_id = attachment.id
        except Exception as e:
            _logger.error(f"Error al generar el PDF del pedido: {str(e)}")
        
        # Mensaje predeterminado que incluye información del pedido
        default_message = f"Estimado {self.partner_id.name},\n\nAdjunto encontrará su {_('Presupuesto') if self.state in ('draft', 'sent') else _('Pedido')} {self.name} por un monto de {self.amount_total} {self.currency_id.name}.\n\nGracias por su atención."
        
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
                'default_related_record_model': self._name,
                'default_related_record_id': self.id,
                'default_use_template': False,  # Cambiado de True a False
            },
        }