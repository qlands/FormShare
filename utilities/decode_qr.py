import base64
import zlib
import json

"""
This small script decodes a ODK Collect QR
Use any QR reader from the Web or on your mobile device to get string encoded in the QR.
Replace QR_string for that string. 
"""

QR_string = "eJwtjl1rAjEQRX9Lg49CVqVUfSss2rKFClIKfQnTzaip+XIy2dXK/vdmoY+Xczn33sURPRJYsb6LhNQhqUwliRNzTGsp3WJZVbKbyTPeZNptX862r3bN6mOzmWz1Q573uTarLk6ea2ou+/DG73qP9tI116/jIs/5l5ev2Tzi55OuZaTwgy0nORNTcQjkVI4aGJULGsuqA25PCq/Qsr2VCmQOCb0uqDcHo8Br1aK12QKJYSr+feN7D240RMr4DSMD7YwvZBj+AK6DUAQ="
QR_binary = base64.b64decode(QR_string)
json_data = json.loads(zlib.decompress(QR_binary))
print(json.dumps(json_data, indent=2))
