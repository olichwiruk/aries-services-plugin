PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/schema-exchange/1.0"
PROTOCOL_PACKAGE = "acapy_plugin.schema_exchange"

SCHEMA_EXCHANGE = f"{PROTOCOL_URI}/schema-exchange"
SCHEMA_EXCHANGE_RESPONSE = f"{PROTOCOL_URI}/schema-exchange-response"

MESSAGE_TYPES = {
    SCHEMA_EXCHANGE: f"{PROTOCOL_PACKAGE}.SchemaExchange",
    SCHEMA_EXCHANGE_RESPONSE: f"{PROTOCOL_PACKAGE}.SchemaExchangeResponse",
}
