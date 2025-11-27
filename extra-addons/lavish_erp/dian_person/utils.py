
from typing import Union, Dict, TypeVar

from bs4 import BeautifulSoup, Tag
from requests import post
from requests.models import Response


from .custom_types import RutStatusDict
from .exceptions import TokenException

FORM_CLASS_INFO = '.tipoFilaNormalVerde'

TOKEN_FIELD = 'com.sun.faces.VIEW'

FORM_PREFIX = 'vistaConsultaEstadoRUT:formConsultaEstadoRUT'

VALUE_ATTR = 'value'

NATURAL_PERSON_VALUES = ['primerNombre', 'otrosNombres', 'primerApellido', 'segundoApellido']

PERSON_MAIN_VALUES_KEYS = [ 'check_digit', 'status', 'name']

PERSON_VALUES_KEYS = ['tin', *PERSON_MAIN_VALUES_KEYS]

WEB_RUT_MUISCA_URL = 'https://muisca.dian.gov.co/WebRutMuisca/DefConsultaEstadoRUT.faces'

DEFAULT_TIMEOUT = 10

DEFAULT_ATTEMPTS = 5

WebMuiscaFormToken = TypeVar('WebMuiscaFormToken')

def remove_none_elements_from_dict(d: dict) -> Dict:
    return {key: value for key, value in d.items() if value is not None and value != ''}


def list_contains_elements_of_list(a:list, b:list)->bool:
    return  all(item in a for item in b)


def as_form_field(field_name:str='')->str:
    return FORM_PREFIX + ':' + field_name if field_name else FORM_PREFIX

def get_soup(response:Response)->Union[BeautifulSoup, None]:
    return BeautifulSoup(response.text, features='html.parser') if response and isinstance(response, Response) else None

def get_value_from_tag(tag:Tag, value:str)->Union[str, None]:
    return tag.contents[0] if tag.contents else tag.attrs.get(value, None)


def find_value_in_soup(soup:BeautifulSoup, value:str)->Union[str, None]:

    tag = soup.find(attrs={'id': as_form_field(value)})

    return None if not tag else get_value_from_tag(tag=tag, value=VALUE_ATTR)

def concat_full_name_by_name_strings(names:list)->Union[str, None]:
    return ' '.join(names) if all(names) else None


def get_web_muisca_form_token()->Union[WebMuiscaFormToken, None]:
    try:
        soup = get_soup(response=post(url=WEB_RUT_MUISCA_URL))
        form_token_field  = soup.find(attrs={"name": TOKEN_FIELD})
        return form_token_field.attrs.get(VALUE_ATTR, None)
    except Exception as e:
        raise TokenException


def get_person_name_from_soup(soup:BeautifulSoup)->Union[str, None]:

    name = find_value_in_soup(soup=soup, value='razonSocial')

    return name if name else concat_full_name_by_name_strings([find_value_in_soup(soup=soup, value=value) for value in NATURAL_PERSON_VALUES])


def get_person_rut_status_from_soup(soup:BeautifulSoup)->Union[RutStatusDict, None]:

    person_data = {PERSON_VALUES_KEYS[0]: find_value_in_soup(soup=soup, value='numNit'),
                     PERSON_VALUES_KEYS[1]: find_value_in_soup(soup=soup, value='dv'),
                     PERSON_VALUES_KEYS[2]: find_value_in_soup(soup=soup, value='estado'),
                     PERSON_VALUES_KEYS[3]: get_person_name_from_soup(soup=soup)}

    person_data = remove_none_elements_from_dict(d=person_data)

    return person_data if list_contains_elements_of_list(a=list(person_data.keys()), b=PERSON_MAIN_VALUES_KEYS) else None 


PAYLOAD_DATA = {as_form_field('modoPresentacionSeleccionBO'): 'pantalla',
                as_form_field('siguienteURL'): '',
                as_form_field('modoPresentacionFormBO'): 'pantalla',
                as_form_field('modoOperacionFormBO'): '',
                as_form_field('mantenerCriterios'): '',
                as_form_field('btnBuscar.x'): 48,
                as_form_field('btnBuscar.y'): 11,
                as_form_field(): 'vistaConsultaEstadoRUT:formConsultaEstadoRUT',
                as_form_field('_idcl'): '',
                }