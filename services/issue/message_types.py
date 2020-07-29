from ..util import generate_model_schema
from marshmallow import Schema, fields
from aries_cloudagent.messaging.agent_message import AgentMessage, AgentMessageSchema
from ..discovery.models import ConsentSchema, ServiceSchema

# Message Types
PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/verifiable-services/1.0"
PROTOCOL_PACKAGE = "services.issue.handlers"


APPLICATION = f"{PROTOCOL_URI}/application"
CONFIRMATION = f"{PROTOCOL_URI}/confirmation"

MESSAGE_TYPES = {
    APPLICATION: f"{PROTOCOL_PACKAGE}.Application",
    CONFIRMATION: f"{PROTOCOL_PACKAGE}.Confirmation",
}


# Messages
Application, ApplicationSchema = generate_model_schema(
    name="Application",
    handler=f"{PROTOCOL_PACKAGE}.ApplicationHandler",
    msg_type=APPLICATION,
    schema={
        "label": fields.Str(required=True),
        "exchange_id": fields.Str(required=True),
    },
)

Confirmation, ConfirmationSchema = generate_model_schema(
    name="Confirmation",
    handler=f"{PROTOCOL_PACKAGE}.ConfirmationHandler",
    msg_type=CONFIRMATION,
    schema={
        "exchange_id": fields.Str(required=True),
        "state": fields.Str(required=True),
    },
)
