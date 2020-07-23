from ..message_types import PROTOCOL_URI

PROTOCOL_PACKAGE = "services.discovery.discovery"

DISCOVERY = f"{PROTOCOL_URI}/discovery"
DISCOVERY_RESPONSE = f"{PROTOCOL_URI}/discovery-response"

MESSAGE_TYPES = {
    DISCOVERY: f"{PROTOCOL_PACKAGE}.Discovery",
    DISCOVERY_RESPONSE: f"{PROTOCOL_PACKAGE}.DiscoveryResponse",
}

# Messages

Discovery, DiscoverySchema = generate_model_schema(
    name="Discovery",
    handler=f"{PROTOCOL_PACKAGE}.DiscoveryHandler",
    msg_type=DISCOVERY,
    schema={},
)


class DiscoveryServiceSchema(Schema):
    label = fields.Str(required=True)
    service_schema = fields.Nested(ServiceSchema())
    consent_schema = fields.Nested(ConsentSchema())


class DiscoveryResponse(AgentMessage):
    class Meta:
        handler_class = f"{PROTOCOL_PACKAGE}.DiscoveryResponseHandler"
        message_type = DISCOVERY_RESPONSE
        schema_class = "DiscoveryResponseSchema"

    def __init__(self, *, services: DiscoveryServiceSchema = None, **kwargs):
        super(DiscoveryResponse, self).__init__(**kwargs)
        self.services = services


class DiscoveryResponseSchema(AgentMessageSchema):
    """DiscoveryResponse message schema used in serialization/deserialization."""

    class Meta:
        model_class = DiscoveryResponse

    services = fields.List(fields.Nested(DiscoveryServiceSchema()), required=True,)
