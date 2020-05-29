PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/acapy-plugin/1.0"
ADD = f"{PROTOCOL_URI}/add"
GET = f"{PROTOCOL_URI}/get"


PROTOCOL_PACKAGE = "acapy_plugin"
MESSAGE_TYPES = {
    ADD: f"{PROTOCOL_PACKAGE}.messages.RecordsAdd",
    GET: f"{PROTOCOL_PACKAGE}.messages.RecordsGet",
}
