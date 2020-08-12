from ..util import generate_model_schema
from marshmallow import Schema, fields
from aries_cloudagent.messaging.agent_message import AgentMessage, AgentMessageSchema
from ..discovery.models import ConsentSchema, ServiceSchema

# Message Types
PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/verifiable-services/1.0"
PROTOCOL_PACKAGE = "services.issue.handlers"


APPLICATION = f"{PROTOCOL_URI}/application"
CONFIRMATION = f"{PROTOCOL_URI}/confirmation"
GET_ISSUE = f"{PROTOCOL_URI}/get-issue"
RECEIVE_ISSUE = f"{PROTOCOL_URI}/receive-issue"

MESSAGE_TYPES = {
    APPLICATION: f"{PROTOCOL_PACKAGE}.Application",
    CONFIRMATION: f"{PROTOCOL_PACKAGE}.Confirmation",
    GET_ISSUE: f"{PROTOCOL_PACKAGE}.GetIssue",
    RECEIVE_ISSUE: f"{PROTOCOL_PACKAGE}.ReceiveIssue",
}


# Messages
Application, ApplicationSchema = generate_model_schema(
    name="Application",
    handler=f"{PROTOCOL_PACKAGE}.ApplicationHandler",
    msg_type=APPLICATION,
    schema={
        "service_id": fields.Str(required=True),
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

GetIssue, GetIssueSchema = generate_model_schema(
    name="GetIssue",
    handler=f"{PROTOCOL_PACKAGE}.GetIssueHandler",
    msg_type=GET_ISSUE,
    schema={"issue_id": fields.Str(required=True),},
)

ReceiveIssue, ReceiveIssueSchema = generate_model_schema(
    name="ReceiveIssue",
    handler=f"{PROTOCOL_PACKAGE}.ReceiveIssueHandler",
    msg_type=RECEIVE_ISSUE,
    schema={
        "label": fields.Str(required=False),
        "payload": fields.Str(required=False),
        "consent_schema": fields.Str(required=False),
        "service_schema": fields.Str(required=False),
    },
)
