import redis
import logging
import os

_logger = logging.getLogger(__name__)

class RedisCache:
    # Get the Redis connection details environment variables
    REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
    REDIS_PORT = os.getenv("REDIS_PORT", 6379)
    REDIS_DB = os.getenv("REDIS_DB", 0)

    #'odoo-cache.ovv209.ng.0001.use2.cache.amazonaws.com'

    def __init__(self, host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB):
        """
        Inicializa la conexión a Redis.

        :param host: Dirección del servidor Redis.
        :param port: Puerto del servidor Redis.
        :param db: Base de datos de Redis a utilizar.
        """
        self.client = redis.StrictRedis(host=host, port=port, db=db)

    def set_value(self, key, value, ex=None):
        """
        Almacena un valor en Redis.

        :param key: Clave para almacenar el valor.
        :param value: Valor a almacenar.
        :param ex: Tiempo de expiración en segundos (opcional).
        """
        try:
            self.client.set(key, value, ex=ex)
            _logger.info(f"Valor almacenado en Redis con clave: {key}")
        except redis.RedisError as e:
            _logger.error(f"Error al almacenar el valor en Redis: {e}")

    def get_value(self, key):
        """
        Recupera un valor de Redis.

        :param key: Clave del valor a recuperar.
        :return: Valor almacenado en Redis o None si no existe.
        """
        try:
            value = self.client.get(key)
            if value:
                _logger.info(f"Valor recuperado de Redis con clave: {key}")
                return value.decode('utf-8')
            else:
                _logger.info(f"No se encontró valor en Redis para la clave: {key}")
                return None
        except redis.RedisError as e:
            _logger.error(f"Error al recuperar el valor de Redis: {e}")
            return None

    def delete_value(self, key):
        """
        Elimina un valor de Redis.

        :param key: Clave del valor a eliminar.
        """
        try:
            self.client.delete(key)
            _logger.info(f"Valor eliminado de Redis con clave: {key}")
        except redis.RedisError as e:
            _logger.error(f"Error al eliminar el valor de Redis: {e}")