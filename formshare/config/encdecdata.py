import base64
import hmac
import logging
from formshare.processes.logging.loggerclass import SecretLogger
import traceback

# from Crypto.Cipher import AES
from cryptography.fernet import Fernet

logging.setLoggerClass(SecretLogger)
log = logging.getLogger("formshare")


def old_decode_data_with_key(data, key):  # pragma: no cover
    """
    Old decode code based on PyCrypto. Here only to migrate 2.0.0 versions
    of FormShare to new versions
    :param data: Data to encrypt
    :param key: Key to use
    :return:
    """
    raise NotImplementedError()


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
    try:
        return f.decrypt(data)
    except Exception as e:
        log.error("Error when decrypting a password. Error: {}".format(str(e)))
        return ""


# Every Fernet token starts so: its version byte and the high bytes of its
# time. An API secret as FormShare makes one, a hex string, never does.
FERNET_PREFIX = "gAAAAA"


def stored_secret(request, stored):
    """An API secret as it was given, from how it is stored, or None when
    there is none to read.

    FormShare stores API secrets encrypted (encode_data), but createsuperuser
    and the Users page stored them as given until 2026-11-23: a value that is
    not a Fernet token is read as given. One that is and does not decrypt
    (another aes.key) is no secret."""
    if stored is None:
        return None
    if isinstance(stored, bytes):
        stored = stored.decode()
    if stored == "":
        return None
    if not stored.startswith(FERNET_PREFIX):
        return stored
    secret = decode_data(request, stored.encode())
    if not isinstance(secret, bytes) or secret == b"":
        return None
    return secret.decode()


def secret_matches(request, stored, given):
    """Whether a secret given matches the one stored, in constant time."""
    secret = stored_secret(request, stored)
    if secret is None or given is None:
        return False
    return hmac.compare_digest(secret.encode(), str(given).encode())


def stored_as_given(stored):
    """Whether a stored secret is kept as given rather than encrypted."""
    if isinstance(stored, bytes):
        stored = stored.decode()
    return bool(stored) and not stored.startswith(FERNET_PREFIX)


def encode_data_with_key(data, key):
    key = base64.b64encode(key)
    f = Fernet(key)
    if not isinstance(data, bytes):
        data = data.encode()
    return f.encrypt(data)


def decode_data_with_key(data, key):
    key = base64.b64encode(key)
    f = Fernet(key)
    try:
        return f.decrypt(data)
    except Exception as e:
        log.error("Error when decrypting a password. Error: {}".format(str(e)))
        log.error(traceback.format_exc())
        return ""
