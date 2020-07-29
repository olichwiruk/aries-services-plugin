PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/verifiable-services/1.0"

PROTOCOL_PACKAGE = "services.discovery.discovery"

DISCOVERY = f"{PROTOCOL_URI}/discovery"
DISCOVERY_RESPONSE = f"{PROTOCOL_URI}/discovery-response"

MESSAGE_TYPES = {
    DISCOVERY: f"{PROTOCOL_PACKAGE}.Discovery",
    DISCOVERY_RESPONSE: f"{PROTOCOL_PACKAGE}.DiscoveryResponse",
}

# Messages
from ..util import generate_model_schema
from marshmallow import Schema, fields
from .models import ServiceSchema, ConsentSchema
from aries_cloudagent.messaging.agent_message import AgentMessage, AgentMessageSchema

Discovery, DiscoverySchema = generate_model_schema(
    name="Discovery",
    handler=f"{PROTOCOL_PACKAGE}.DiscoveryHandler",
    msg_type=DISCOVERY,
    schema={},
)


class DiscoveryServiceSchema(Schema):
    label = fields.Str(required=True)
    service_id = fields.Str(required=True)
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
