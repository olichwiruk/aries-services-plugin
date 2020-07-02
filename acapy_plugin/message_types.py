PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/schema-exchange/1.0"
PROTOCOL_PACKAGE = "acapy_plugin.schema_exchange"

REQUEST = f"{PROTOCOL_URI}/request"
RESPONSE = f"{PROTOCOL_URI}/response"

MESSAGE_TYPES = {
    REQUEST: f"{PROTOCOL_PACKAGE}.Request",
    RESPONSE: f"{PROTOCOL_PACKAGE}.Response",
}
