import aries_cloudagent.wallet.crypto as crypto
import base58
import json
import uuid

# a bit of a hack to simplify message unpacking,
# decode_pack_message needs a callable object for some reason
def unpackMessage(message, privateKey):
    class FindKey:
        def __init__(self, key):
            self.key = key

        def __call__(self, argument):
            return self.key

    find_key = FindKey(privateKey)
    return crypto.decode_pack_message(message, find_key)


# packs a dictionary into a encoded message
def packMessage(message: dict, connection: dict) -> bytes:
    # pass in our private key and recipient key to the encode_pack_message
    decodedRecipientKey = base58.b58decode(
        connection["DIDDoc"]["service"][0]["recipientKeys"][0]
    )
    packedMessage = crypto.encode_pack_message(
        json.dumps(message), [decodedRecipientKey], connection["myKey"]
    )
    return packedMessage.decode("ascii")


# parameters are dict items you want to pass into the message
# e.g. buildMessage(
#    "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/discover-features/1.0/query",
#    payload="aaa")
def buildMessage(protocol: str, **parameters) -> dict:
    message = {}
    message["@id"] = str(uuid.uuid4())
    message["@type"] = protocol
    message["~transport"] = {}
    message["~transport"]["return_route"] = "all"
    for name, value in parameters.items():
        message[name] = value
    return message
