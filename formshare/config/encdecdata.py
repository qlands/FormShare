from Crypto.Cipher import AES
import base64
from cryptography.fernet import Fernet


def old_decode_data_with_key(data, key):
    """
        Old decode code based on PyCrypto. Here only to migrate 2.0.0 versions
        of FormShare to new versions
        :param data: Data to encrypt
        :param key: Key to use
        :return:
        """
    byte_padding = b"|"

    def decode_aes(c, e):
        return c.decrypt(base64.b64decode(e)).rstrip(byte_padding)

    cipher = AES.new(key, 1)
    return decode_aes(cipher, data)


def encode_data(request, data):
    key = request.registry.settings["aes.key"].encode()
    key = base64.b64encode(key)
    f = Fernet(key)
    if not isinstance(data, bytes):
        data = data.encode()
    return f.encrypt(data)


def decode_data(request, data):
    key = request.registry.settings["aes.key"].encode()
    key = base64.b64encode(key)
    f = Fernet(key)
    return f.decrypt(data)


def encode_data_with_key(data, key):
    key = base64.b64encode(key)
    f = Fernet(key)
    if not isinstance(data, bytes):
        data = data.encode()
    return f.encrypt(data)
