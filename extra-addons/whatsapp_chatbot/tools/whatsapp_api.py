# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import requests
import threading
import json

from odoo import _
from odoo.exceptions import RedirectWarning
from odoo.addons.whatsapp.tools.whatsapp_exception import WhatsAppError
from odoo.addons.whatsapp.tools.whatsapp_api import WhatsAppApi

_logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = "https://graph.facebook.com/v17.0"

class WhatsAppApi(WhatsAppApi):

    def __api_requests(self, request_type, url, auth_type="", params=False, headers=None, data=False, files=False, endpoint_include=False):
        _logger.info("API Request3: %s %s", request_type, url)
        if getattr(threading.current_thread(), 'testing', False):
            raise WhatsAppError("API requests disabled in testing.")

        headers = headers or {}
        params = params or {}
        if not all([self.token, self.phone_uid]):
            action = self.wa_account_id.env.ref('whatsapp.whatsapp_account_action')
            raise RedirectWarning(_("To use WhatsApp Configure it first"), action=action.id, button_text=_("Configure Whatsapp Business Account"))
        if auth_type == 'oauth':
            headers.update({'Authorization': f'OAuth {self.token}'})
        if auth_type == 'bearer':
            headers.update({'Authorization': f'Bearer {self.token}'})
        call_url = (DEFAULT_ENDPOINT + url) if not endpoint_include else url

        try:
            res = requests.request(request_type, call_url, params=params, headers=headers, data=data, files=files, timeout=10)
        except requests.exceptions.RequestException:
            raise WhatsAppError(failure_type='network')

        # raise if json-parseable and 'error' in json
        try:
            for chunk in res.iter_content(chunk_size=1024):
                chunk_data = chunk.decode('utf-8')
                if 'error' in chunk_data:
                    response_data = json.loads(chunk_data)
                    raise WhatsAppError(*self._prepare_error_response(response_data))
        except ValueError:
            if not res.ok:
                raise WhatsAppError(failure_type='network')

        return res