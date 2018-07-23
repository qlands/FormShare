#Code from http://www.codekoala.com/posts/aes-encryption-python-using-pycrypto/

from Crypto.Cipher import AES
import base64


# the block size for the cipher object; must be 16, 24, or 32 for AES
BLOCK_SIZE = 32

#EncKey = "%e[~faXa.kp&<wUM&C3NLG3?/pBv4hW&"

# the character used for padding--with a block cipher such as AES, the value
# you encrypt must be a multiple of BLOCK_SIZE in length.  This character is
# used to ensure that your value is always a multiple of BLOCK_SIZE
PADDING = '|'
BPADDING = b'|'

# one-liner to sufficiently pad the text to be encrypted
pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * PADDING

# one-liners to encrypt/encode and decrypt/decode a string
# encrypt with AES, encode with base64
EncodeAES = lambda c, s: base64.b64encode(c.encrypt(pad(s)))
DecodeAES = lambda c, e: c.decrypt(base64.b64decode(e)).rstrip(BPADDING)

def encodeData(request,data):
    secret = request.registry.settings['aes.key']
    cipher = AES.new(secret)
    return EncodeAES(cipher, data)

def decodeData(request,data):
    secret = request.registry.settings['aes.key']
    cipher = AES.new(secret)
    return DecodeAES(cipher, data)

def encodeDataWithAESKey(data,key):
    cipher = AES.new(key)
    return EncodeAES(cipher, data)