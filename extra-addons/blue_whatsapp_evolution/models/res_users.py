# -*- coding: utf-8 -*-
#############################################################################
#
#    BlueConnect Solutions Ltda.
#
#    Copyright (C) 2023-TODAY BlueConnect Solutions (<https://www.blueconnect.com.br>)
#    Autor: Diego Santos (diego.blueconenct@gmail.com)
#
#    Puede modificarlo bajo los términos de la
#    LICENCIA PÚBLICA GENERAL MENOR DE GNU (LGPL v3), Versión 3.
#
#    Este programa se distribuye con la esperanza de que sea útil,
#    pero SIN NINGUNA GARANTÍA; incluso sin la garantía implícita de
#    COMERCIABILIDAD o IDONEIDAD PARA UN PROPÓSITO PARTICULAR. Vea la
#    LICENCIA PÚBLICA GENERAL MENOR DE GNU (LGPL v3) para más detalles.
#
#    Debería haber recibido una copia de la LICENCIA PÚBLICA GENERAL MENOR DE GNU
#    (LGPL v3) junto con este programa.
#    Si no, vea <http://www.gnu.org/licenses/>.
#
#############################################################################

from odoo import models, fields, api, _
import json
import requests
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ResUsers(models.Model):
    _inherit = 'res.users'

    evolution_api_url = fields.Char(
        string="URL da API Evolution",
        help="URL base da API Evolution usada para integração pelo usuário"
    )
    evolution_global_token = fields.Char(
        string="Token Global da API Evolution",
        help="Token global da API Evolution do usuário"
    )
    evolution_api_instance = fields.Char(
        string="Instância da API Evolution",
        help="Instância da API Evolution usada para integração pelo usuário"
    )
    use_company_whatsapp = fields.Boolean(
        string="Usar Configuração da Empresa",
        default=True,
        store=True,  # Asegura que el campo se almacene en la base de datos
        help="Se marcado, usará as configurações de WhatsApp da empresa"
    )

    def get_whatsapp_credentials(self):
        """Retorna as credenciais do usuário"""
        self.ensure_one()
        # Removida a lógica de company temporariamente
        return {
            'api_url': self.evolution_api_url,
            'token': self.evolution_global_token,
            'instance': self.evolution_api_instance,
        }

    def action_test_whatsapp_api(self):
        """Testa a conexão com a API do WhatsApp usando as credenciais do usuário"""
        self.ensure_one()
        credentials = self.get_whatsapp_credentials()
        
        if not all(credentials.values()):
            raise UserError(_("Todos os campos de configuração do WhatsApp são obrigatórios."))

        url = f"{credentials['api_url']}/instance/connectionState/{credentials['instance']}"
        headers = {
            'apikey': credentials['token']
        }

        try:
            response = requests.get(url, headers=headers)
            response_data = response.json()

            connection_state = response_data.get('instance', {}).get('state', 'close')

            if connection_state == 'open':
                message = "✅ Conexão com a API estabelecida."
            else:
                message = "❌ A conexão com a API foi recusada."

            response_record = self.env['api.response'].create({
                'response': message
            })

            return {
                'name': 'Resposta da API',
                'type': 'ir.actions.act_window',
                'res_model': 'api.response',
                'view_mode': 'form',
                'view_id': False,
                'res_id': response_record.id,
                'target': 'new',
            }

        except requests.RequestException as e:
            raise UserError(_("Erro ao fazer requisição: %s") % str(e))

    def verify_evolution_credentials(self):
        """Verifica que el usuario actual tiene credenciales válidas para Evolution API"""
        self.ensure_one()
        credentials = self.get_whatsapp_credentials()
        
        if not all([credentials.get('api_url'), credentials.get('token'), credentials.get('instance')]):
            raise UserError(_("Configure sus credenciales de WhatsApp en su perfil de usuario"))
        
        return credentials