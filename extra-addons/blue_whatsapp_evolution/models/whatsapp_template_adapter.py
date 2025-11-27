# -*- coding: utf-8 -*-
import json
import logging
import requests
import re
from lxml import html, etree
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class WhatsAppTemplateAdapter(models.Model):
    _inherit = 'whatsapp.template'
    
    use_evolution_api = fields.Boolean(
        string="Use Evolution API",
        help="If checked, this template will be sent using Evolution API instead of WhatsApp Business API"
    )
    
    def send_template_evolution(self, record):
        """Send WhatsApp template using Evolution API (text message fallback method)"""
        self.ensure_one()
        
        if not record:
            raise UserError(_("No record provided to send template message"))
        
        # Get user credentials for Evolution API
        current_user = self.env.user
        if not hasattr(current_user, 'get_whatsapp_credentials'):
            raise UserError(_("Your user doesn't have WhatsApp Evolution API configuration"))
            
        credentials = current_user.get_whatsapp_credentials()
        
        # Get phone number
        phone = self._get_recipient_phone_from_record(record)
        if not phone:
            raise UserError(_("No phone number found for the recipient"))
        
        # CAMBIO PRINCIPAL: Usar endpoint sendText en lugar de sendTemplate
        url = f"{credentials['api_url']}/message/sendText/{credentials['instance']}"
        headers = {
            'apikey': credentials['token'],
            'Content-Type': 'application/json'
        }
        
        # Preparar el contenido del mensaje usando el cuerpo de la plantilla con variables reemplazadas
        try:
            formatted_message = self._get_formatted_body_for_evolution(record)
            _logger.info(f"Formatted message for template: {formatted_message}")
        except Exception as e:
            _logger.error(f"Error formatting template body: {str(e)}")
            raise UserError(_("Error formatting template message: %s") % str(e))
        
        # Preparar el payload para mensaje de texto
        payload = {
            "number": phone,
            "text": formatted_message,
            "linkPreview": False,
            "mentionsEveryOne": False,
        }
        
        # Send request to Evolution API
        try:
            _logger.info(f"Sending template (as text) to Evolution API with payload: {json.dumps(payload, indent=2)}")
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response_json = {}
            
            try:
                response_json = response.json()
            except Exception:
                response_json = {"error": "No JSON response"}
            
            _logger.info(f"Evolution API response: Status {response.status_code} - {json.dumps(response_json, indent=2)}")
            
            if response.status_code in [200, 201]:
                # Log the message
                self._log_sent_message(record, phone, self.name, response.status_code)
                
                # Mostrar notificación y cerrar ventana usando un enfoque compatible
                self.env['bus.bus']._sendone(
                    self.env.user.partner_id,
                    'simple_notification',
                    {
                        'title': _('WhatsApp'),
                        'message': _('Template sent successfully (as text message)'),
                        'sticky': False,
                        'type': 'success',  # Usar 'success' en lugar de 'warning: False'
                    }
                )
                
                # Devolver simplemente la acción para cerrar la ventana
                return {
                    'type': 'ir.actions.act_window_close'
                }
            else:
                _logger.error(f"Error sending template via Evolution API: {response.text}")
                self._log_sent_message(record, phone, self.name, 'failed')
                raise UserError(_("Failed to send template: %s") % response.text)
        except Exception as e:
            _logger.error(f"Exception sending template via Evolution API: {str(e)}")
            self._log_sent_message(record, phone, self.name, 'failed')
            raise UserError(_("Error sending template: %s") % str(e))
    
    def _get_formatted_body_for_evolution(self, record):
        """Get template body with variables replaced for Evolution API text message"""
        # Obtener el cuerpo de la plantilla
        message_body = self.body
        if not message_body:
            return ""
        
        # Reemplazar variables en el cuerpo
        variable_values = {}
        for var in self.variable_ids.filtered(lambda v: v.line_type == 'body'):
            try:
                if var.field_type == 'field' and var.field_name:
                    variable_values[var.name] = str(var._find_value_from_field_chain(record))
                else:
                    variable_values[var.name] = var.demo_value
            except Exception as e:
                _logger.warning(f"Error getting variable {var.name}: {str(e)}")
                variable_values[var.name] = var.demo_value or "N/A"
        
        # Aplicar reemplazos en el mensaje
        formatted_message = message_body
        for name, value in variable_values.items():
            formatted_message = formatted_message.replace(name, value)
        
        # Añadir cabecera si existe
        if self.header_type == 'text' and self.header_text:
            header_text = self.header_text
            
            # Reemplazar variables en la cabecera
            for var in self.variable_ids.filtered(lambda v: v.line_type == 'header'):
                try:
                    if var.field_type == 'field' and var.field_name:
                        value = str(var._find_value_from_field_chain(record))
                    else:
                        value = var.demo_value
                    header_text = header_text.replace(var.name, value)
                except Exception as e:
                    _logger.warning(f"Error getting header variable: {str(e)}")
                    header_text = header_text.replace(var.name, var.demo_value or "N/A")
            
            formatted_message = f"*{header_text}*\n\n{formatted_message}"
        
        # Añadir pie de página si existe
        if self.footer_text:
            formatted_message = f"{formatted_message}\n\n_{self.footer_text}_"
        
        return formatted_message
    
    def _get_recipient_phone_from_record(self, record):
        """Get recipient phone number from record using the configured phone_field"""
        if not self.phone_field:
            return None
            
        try:
            # Handle nested fields (partner_id.mobile)
            value = record
            for field in self.phone_field.split('.'):
                value = value[field]
                if not value:
                    return None
            
            # Clean phone number (keep only digits)
            if value:
                return re.sub(r'[^0-9]', '', value)
            return None
        except Exception as e:
            _logger.error(f"Error extracting phone: {str(e)}")
            return None
    
    def _log_sent_message(self, record, phone, template_name, status):
        """Log sent message to chatter"""
        status_text = 'enviada correctamente' if status not in ['failed', 'error'] else 'falló al enviar'
        body = f"<p>Plantilla WhatsApp '{template_name}' {status_text} al número {phone}</p>"
        
        # Log in chatter
        record.message_post(body=body)
        
        # Also create a record in blue.whatsapp.message model if it exists
        if self.env.get('blue.whatsapp.message'):
            partner_id = None
            if hasattr(record, 'partner_id') and record.partner_id:
                partner_id = record.partner_id.id
            elif record._name == 'res.partner':
                partner_id = record.id
                
            if partner_id:
                self.env['blue.whatsapp.message'].create({
                    'partner_id': partner_id,
                    'message': f"Template: {template_name}",
                    'status': 'sent' if status not in ['failed', 'error'] else 'failed',
                    'template_id': self.id,
                })

    def action_send_template(self, record):
        """Override to use Evolution API when configured"""
        self.ensure_one()
        
        # If using Evolution API, send with custom method
        if self.use_evolution_api:
            return self.send_template_evolution(record)
        
        # Otherwise, use the standard WhatsApp Business API method
        return super().action_send_template(record)