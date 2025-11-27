from typing import Union

import requests
from requests.models import Request

from .custom_types import RutStatusDict

from . import utils



def get_person_rut_status(tin:str, token:str='', attempts:int=utils.DEFAULT_ATTEMPTS, timeout:int=utils.DEFAULT_TIMEOUT)->Union[RutStatusDict, None]:

    """This function will returns a Person Rut Status information stored inside a Dict

    Args:
        tin: a string that represents a Person's Tax Identification Number in Colombia.

        attempts: an integer which represents the number of seconds to retry the function (5 by default)

        timeout: an integer which representes the number of seconds to sleep in case of a request timeout (10 by default)

    Raises:
        TokenException: When the request's token is missing or is a blank string

    Returns:
        RutStatusDict: A typed dictionary with the main key and values from an actual legal or natural person
        None: A person with the requested TIN is not found or there is an error on the code in execution
    """

    if not token or isinstance(token, str) is False:
        token = utils.get_web_muisca_form_token()

    if attempts == 0:
        print('All attempts completed! ')
        return

    try:
        response = requests.post(url=utils.WEB_RUT_MUISCA_URL, data={**utils.PAYLOAD_DATA, utils.as_form_field('numNit'): tin, utils.TOKEN_FIELD: token}, timeout=timeout)

        if isinstance(response, Request):
            response.raise_for_status()

    except requests.Timeout:
        return get_person_rut_status(tin=tin, token=token, attempts=attempts-1)
    except Exception as e:
        print(e)
    else:
        soup = utils.get_soup(response=response)
        return None if not soup else utils.get_person_rut_status_from_soup(soup=soup)
