"""Message type identifiers for Hello world."""

PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/hello-world/1.0"

DISCLOSE = f"{PROTOCOL_URI}/disclose"
QUERY = f"{PROTOCOL_URI}/query"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.helloworld"

MESSAGE_TYPES = {
    DISCLOSE: f"{PROTOCOL_PACKAGE}.messages.disclose.Disclose",
    QUERY: f"{PROTOCOL_PACKAGE}.messages.query.Query",
}
