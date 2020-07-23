PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/schema-exchange/1.0"
PROTOCOL_PACKAGE = "acapy_plugin.schema_exchange"

REQUEST = f"{PROTOCOL_URI}/request"
RESPONSE = f"{PROTOCOL_URI}/response"
PLACEHOLDER = f"{PROTOCOL_URI}/placeholder"

MESSAGE_TYPES = {
    REQUEST: f"{PROTOCOL_PACKAGE}.Request",
    RESPONSE: f"{PROTOCOL_PACKAGE}.Response",
    PLACEHOLDER: f"{PROTOCOL_PACKAGE}.Placeholder",
}
