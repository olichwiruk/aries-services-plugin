PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/verifiable-services/1.0"

PROTOCOL_PACKAGE = "services.issue.issue_credential_consentual"
APPLICATION = f"{PROTOCOL_URI}/application"
MESSAGE_TYPES = {APPLICATION: f"{PROTOCOL_PACKAGE}.Application"}

# Messages
from ..util import generate_model_schema
from marshmallow import Schema, fields
from aries_cloudagent.messaging.agent_message import AgentMessage, AgentMessageSchema
from ..discovery.models import ConsentSchema, ServiceSchema

Application, ApplicationSchema = generate_model_schema(
    name="Application",
    handler=f"{PROTOCOL_PACKAGE}.ApplicationHandler",
    msg_type=APPLICATION,
    schema={
        "service_schema": fields.Nested(ServiceSchema()),
        "consent_schema": fields.Nested(ConsentSchema()),
    },
)
