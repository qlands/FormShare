# Code from http://www.codekoala.com/posts/aes-encryption-python-using-pycrypto/

from Crypto.Cipher import AES
import base64
from cryptography.fernet import Fernet


# the block size for the cipher object; must be 16, 24, or 32 for AES
BLOCK_SIZE = 32

# EncKey = "%e[~faXa.kp&<wUM&C3NLG3?/pBv4hW&"

# the character used for padding--with a block cipher such as AES, the value
# you encrypt must be a multiple of BLOCK_SIZE in length.  This character is
# used to ensure that your value is always a multiple of BLOCK_SIZE
PADDING = "|"
BPADDING = b"|"


def pad(s):
    # pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * PADDING
    return s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * PADDING


# encrypt with AES, encode with base64


def encode_aes(c, s):
    # EncodeAES = lambda c, s: base64.b64encode(c.encrypt(pad(s)))
    return base64.b64encode(c.encrypt(pad(s).encode()))


def decode_aes(c, e):
    # DecodeAES = lambda c, e: c.decrypt(base64.b64decode(e)).rstrip(BPADDING)
    return c.decrypt(base64.b64decode(e)).rstrip(BPADDING)


def encode_data(request, data):
    key = request.registry.settings["aes.key"].encode()
    key = base64.b64encode(key)
    f = Fernet(key)
    if not isinstance(data, bytes):
        data = data.encode()
    return f.encrypt(data)


def old_decode_data_with_key(data, key):
    """
    Old decode code based on PyCrypto. Here only to migrate 2.0.0 versions
    of FormShare to new versions
    :param data: Data to encrypt
    :param key: Key to use
    :return:
    """
    cipher = AES.new(key, 1)
    return decode_aes(cipher, data)


def decode_data(request, data):
    key = request.registry.settings["aes.key"].encode()
    key = base64.b64encode(key)
    f = Fernet(key)
    return f.decrypt(data)


def encode_data_with_key(data, key):
    key = base64.b64encode(key)
    f = Fernet(key)
    return f.encrypt(data)
