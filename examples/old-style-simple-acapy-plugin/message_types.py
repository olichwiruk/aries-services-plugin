PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/acapy-plugin/1.0"

QUERY = f"{PROTOCOL_URI}/query"

PROTOCOL_PACKAGE = "acapy-plugin"

MESSAGE_TYPES = {
    QUERY: f"{PROTOCOL_PACKAGE}.messages.query.Query",
}
