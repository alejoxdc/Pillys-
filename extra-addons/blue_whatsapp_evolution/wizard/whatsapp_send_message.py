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
import json
import logging
import requests
import re
from lxml import html, etree
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class WhatsappSendMessage(models.TransientModel):
    """Este modelo es usado para enviar mensajes del WhatsApp a través del Odoo."""
    _name = 'whatsapp.send.message'
    _description = "Wizard de Mensaje WhatsApp"

    user_id = fields.Many2one('res.partner', string="Destinatario", required=True, 
                         help="Contacto al que se enviará el mensaje de WhatsApp")
    mobile = fields.Char(related='user_id.mobile', string="Número de WhatsApp")
    message = fields.Text(string="Mensaje", required=True)
    attachments_ids = fields.Many2many('ir.attachment', string="Archivos Adjuntos")
    move_id = fields.Many2one('account.move', string="Factura relacionada")
    # Este campo necesita esta estructura específica para funcionar con el widget mail_attachments
    mail_attachments_widget = fields.Many2many(
        'ir.attachment',
        'whatsapp_message_attachment_rel', 
        'whatsapp_message_id',
        'attachment_id',
        string='Adjuntos',
        required=False,
        copy=False,
        attachment=True,  # Esto es crucial para el widget
    )
    
    use_template = fields.Boolean(string="Use Template", default=False)
    template_id = fields.Many2one('whatsapp.template', string="Template") # Cambia de blue.whatsapp.template a whatsapp.template
    related_record_id = fields.Integer(string="Related Record ID")
    related_record_model = fields.Char(string="Related Record Model")

    @api.model
    def default_get(self, fields):
        res = super(WhatsappSendMessage, self).default_get(fields)
        # Inicializar el campo mail_attachments_widget con una lista vacía
        if 'mail_attachments_widget' in fields and not res.get('mail_attachments_widget'):
            res['mail_attachments_widget'] = []
        return res
    
    @api.onchange('related_record_model')
    def _onchange_related_record_model(self):
        """Filtrar plantillas disponibles según el modelo relacionado"""
        if self.related_record_model:
            return {
                'domain': {
                    'template_id': [('model', '=', self.related_record_model)]
                }
            }

    @api.onchange('use_template', 'template_id')
    def _onchange_template(self):
        """Actualizar el mensaje cuando se selecciona una plantilla"""
        if self.use_template and self.template_id and self.related_record_model and self.related_record_id:
            try:
                record = self.env[self.related_record_model].browse(self.related_record_id)
                if record.exists():
                    # Vista previa del cuerpo de la plantilla con valores reales si es posible
                    try:
                        if self.template_id.use_evolution_api:
                            # Para plantillas con Evolution API
                            formatted_body = self.template_id._get_formatted_body_for_evolution(record)
                            self.message = formatted_body
                        elif hasattr(self.template_id, '_get_formatted_body'):
                            # Para plantillas estándar de WhatsApp
                            formatted_body = self.template_id._get_formatted_body(variable_values=record)
                            self.message = formatted_body
                        else:
                            self.message = self.template_id.body
                    except Exception as e:
                        _logger.error(f"Error previewing template body: {str(e)}")
                        self.message = self.template_id.body or ""
            except Exception as e:
                _logger.error(f"Error applying template: {str(e)}")
                self.message = ""

    def prepare_media(self, attachment, message_text):
        """Prepara archivos y texto para API de WhatsApp según la especificación oficial"""
        try:
            # 1. Recoger metadatos básicos
            mime_type = attachment.mimetype
            file_name = attachment.name
            media_type = 'document'
            
            # 2. Determinar tipo de medio correcto
            type_mapping = {
                'image': ['image/jpeg', 'image/png', 'image/webp'],
                'video': ['video/mp4', 'video/3gp'],
                'document': ['application/pdf', 'text/plain']
            }
            for key, types in type_mapping.items():
                if mime_type in types:
                    media_type = key
                    break

            # 3. Preparar contenido del medio - CORREGIDO PARA MANEJAR BYTES
            if attachment.url:
                media_content = attachment.url
            else:
                # Convertir bytes a string base64 si es necesario
                if isinstance(attachment.datas, bytes):
                    media_content = attachment.datas.decode('utf-8')
                else:
                    media_content = attachment.datas

            # 4. Validar formato final
            if not media_content:
                raise ValueError("No se encontró contenido en el archivo adjunto")

            # Devolver el medio y el texto (mensaje)
            return {
                "media": media_content,
                "mediatype": media_type,
                "mimetype": mime_type,
                "fileName": file_name,
                "caption": message_text
            }

        except Exception as e:
            _logger.error(f"Fallo en la preparación del archivo adjunto: {str(e)}")
            return None

    def action_send_message(self): 
        """Enviar mensaje usando las credenciales del usuario atual"""
        current_user = self.env.user
        
        # Obtener credenciales del usuario actual
        if not (current_user.evolution_api_url and 
                current_user.evolution_global_token and 
                current_user.evolution_api_instance):
            raise UserError(_("Configure suas credenciais de WhatsApp em seu perfil de usuario."))

        # Si está usando una plantilla, usar el método de envío del modelo template
        if self.use_template and self.template_id and self.related_record_model and self.related_record_id:
            try:
                record = self.env[self.related_record_model].browse(self.related_record_id)
                if record.exists():
                    # Asegurarnos de que la plantilla use Evolution API
                    if hasattr(self.template_id, 'use_evolution_api'):
                        self.template_id.use_evolution_api = True
                    return self.template_id.action_send_template(record)
                else:
                    raise UserError(_("El registro relacionado no existe."))
            except Exception as e:
                raise UserError(_("Error sending template: %s") % str(e))
                
        # Limpieza del texto HTML para extraer solo el contenido de texto
        message_text = self.message
        if message_text:
            try:
                # Intentar limpiar el HTML para obtener texto plano
                doc = html.fromstring(message_text)
                message_text = doc.text_content()
            except Exception as e:
                _logger.warning(f"Error al limpiar HTML del mensaje: {str(e)}")
        
        # Verificar que el usuario tiene un número móvil
        if not self.user_id.mobile:
            raise UserError(_("El destinatario no tiene un número de WhatsApp definido."))
            
        # Simplificar para solo usar un campo de adjuntos
        all_attachments = self.attachments_ids
            
        # Definir la URL para envío del mensaje (texto o media)
        if all_attachments:
            url = f"{current_user.evolution_api_url}/message/sendMedia/{current_user.evolution_api_instance}"
        else:
            url = f"{current_user.evolution_api_url}/message/sendText/{current_user.evolution_api_instance}"
        
        # Preparar el payload con el mensaje limpio
        payload = {
            "number": re.sub(r'[^0-9]', '', self.user_id.mobile),
            "text": message_text,
            "linkPreview": False,
            "mentionsEveryOne": False,
        }

        headers = {
            "Content-Type": "application/json",
            'apikey': current_user.evolution_global_token
        }

        media_urls = []
        if all_attachments:
            for attachment in all_attachments:
                media_data = self.prepare_media(attachment, message_text)
                if media_data:
                    media_urls.append(media_data)

        if media_urls:
            payload["media"] = media_urls[0]["media"]
            payload["mediatype"] = media_urls[0]["mediatype"]
            payload["mimetype"] = media_urls[0]["mimetype"]
            payload["fileName"] = media_urls[0]["fileName"]
            payload["caption"] = media_urls[0]["caption"]

        try:
            _logger.info(f"Enviando mensaje a Evolution API con payload: {json.dumps(payload)}")
            response = requests.post(url, data=json.dumps(payload), headers=headers)
            response_data = response.json()
            
            # Registrar la respuesta completa para depuración
            _logger.debug(f"Respuesta de API: {response_data}")
            
            if response.status_code in [200, 201]:
                status = 'sent'
                body = f"✅ Mensaje enviado con éxito a {self.user_id.name} ({self.user_id.mobile})"
                _logger.info(f"Mensaje enviado con éxito a {self.user_id.mobile}")
            else:
                status = 'failed'
                error_msg = response_data.get('error', 'Error desconocido')
                body = f"❌ Error al enviar mensaje: {error_msg}"
                _logger.error(f"Error al enviar mensaje: {response.status_code} - {response.text}")
        except Exception as e:
            status = 'failed'
            body = f"❌ Error al enviar mensaje: {str(e)}"
            _logger.exception(f"Excepción al enviar mensaje: {str(e)}")
            raise UserError(_("Error al enviar mensaje: %s") % str(e))

        # Garantizar que partner_id esté correctamente rellenado
        partner_id = None
        if self.user_id:
            try:
                # Comprobar si el registro actual es un partner
                if self.user_id._name == 'res.partner':
                    partner_id = self.user_id.id
                    _logger.info(f"Usando partner_id directamente: {partner_id}")
                else:
                    _logger.error(f"Erro: Nenhum parceiro associado ao registro. user_id: {self.user_id}.")
            except Exception as e:
                _logger.error(f"Error al obtener partner_id: {str(e)}")

        # Registrar el mensaje en el log de blue.whatsapp.message
        if partner_id:
            try:
                self.env['blue.whatsapp.message'].create({
                    'partner_id': partner_id,
                    'message': message_text,
                    'status': status,
                })
                _logger.info(f"Mensaje registrado para partner_id {partner_id}")
            except Exception as e:
                _logger.error(f"Error al crear registro de mensaje: {str(e)}")
        else:
            _logger.error("No se pudo crear registro de mensaje: partner_id no disponible")

        # Mostrar mensaje en el chatter si hay un related_record_id
        if self.related_record_model and self.related_record_id:
            try:
                record = self.env[self.related_record_model].browse(self.related_record_id)
                if record.exists():
                    record.message_post(body=body, message_type='comment', subtype_xmlid='mail.mt_note')
                    _logger.info(f"Mensaje publicado en el chatter de {self.related_record_model} {self.related_record_id}")
            except Exception as e:
                _logger.error(f"Error al publicar en el chatter: {str(e)}")
        
        # Mostrar notificación y cerrar ventana usando un enfoque compatible con Odoo 17
        self.env['bus.bus']._sendone(
            self.env.user.partner_id,
            'simple_notification',
            {
                'title': _('WhatsApp'),
                'message': body, 
                'sticky': False,
                'type': 'success' if status == 'sent' else 'danger'  # Usar 'success' para verde y 'danger' para rojo
            }
        )
        
        # Devolver simplemente la acción para cerrar la ventana
        return {
            'type': 'ir.actions.act_window_close'
        }

    @api.model
    def _valid_field_parameter(self, field, name):
        # Permitir el parámetro 'attachment' para campos Many2many
        if name == 'attachment' and field.type == 'many2many':
            return True
        return super()._valid_field_parameter(field, name)

