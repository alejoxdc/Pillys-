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
from odoo import models, fields

class BlueWhatsappMessage(models.Model):
    _name = 'blue.whatsapp.message'
    _description = 'WhatsApp Message Log'

    partner_id = fields.Many2one('res.partner', string="Parceiro", help="Parceiro que recebeu a mensagem", required=True)
    lead_id = fields.Many2one('crm.lead', string="Lead", help="Lead que recebeu a mensagem")
    message = fields.Text(string="Mensagem", required=True, help="Conteúdo da mensagem enviada")
    status = fields.Selection([
        ('sent', 'Enviada'),
        ('failed', 'Falhada')
    ], string="Status", required=True, default='sent', help="Status da mensagem")
    sent_date = fields.Datetime(string="Data de Envio", default=fields.Datetime.now, help="Data e hora em que a mensagem foi enviada")
    template_id = fields.Many2one('whatsapp.template', string="Plantilla", help="Plantilla usada para enviar este mensagem")

    def create_log_entry(self, partner, message, status):
        """Método para criar um log de mensagem WhatsApp"""
        lead = partner and partner.parent_id or False
        self.create({
            'partner_id': partner.id,
            'lead_id': lead.id if lead else False,
            'message': message,
            'status': status,
        })

    def log_template_message(self, partner, template_id, status='sent'):
        """Registra un mensaje enviado a través de una plantilla"""
        if not partner:
            _logger.error("No se puede registrar mensaje: el socio es obligatorio")
            return False
        
        vals = {
            'partner_id': partner.id,
            'message': f"Plantilla: {template_id.name}",
            'status': status,
            'template_id': template_id.id if template_id else False,
            'sent_date': fields.Datetime.now(),
        }
        
        try:
            message_id = self.create(vals)
            _logger.info(f"Mensaje de plantilla registrado con ID: {message_id.id}")
            return message_id
        except Exception as e:
            _logger.error(f"Error al registrar mensaje de plantilla: {str(e)}")
            return False
            
    def log_direct_message(self, partner, message_text, status='sent', attachments=None):
        """Registra un mensaje directo enviado"""
        if not partner:
            _logger.error("No se puede registrar mensaje: el socio es obligatorio")
            return False
            
        # Acortar mensaje si es muy largo para el registro
        if message_text and len(message_text) > 500:
            message_text = message_text[:497] + "..."
        
        vals = {
            'partner_id': partner.id,
            'message': message_text,
            'status': status,
            'sent_date': fields.Datetime.now(),
        }
        
        if attachments:
            # Si se implementa un campo para adjuntos, agregarlo aquí
            pass
            
        try:
            message_id = self.create(vals)
            _logger.info(f"Mensaje directo registrado con ID: {message_id.id}")
            return message_id
        except Exception as e:
            _logger.error(f"Error al registrar mensaje directo: {str(e)}")
            return False
