from ..util import generate_model_schema
from marshmallow import Schema, fields
from aries_cloudagent.messaging.agent_message import AgentMessage, AgentMessageSchema
from ..models import ConsentSchema, ServiceSchema

# Message Types
PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/verifiable-services/1.0"
PROTOCOL_PACKAGE = "services.issue.handlers"


APPLICATION = f"{PROTOCOL_URI}/application"
CONFIRMATION = f"{PROTOCOL_URI}/confirmation"
GET_ISSUE = f"{PROTOCOL_URI}/get-issue"
GET_ISSUE_RESPONSE = f"{PROTOCOL_URI}/get-issue-response"

MESSAGE_TYPES = {
    APPLICATION: f"{PROTOCOL_PACKAGE}.Application",
    CONFIRMATION: f"{PROTOCOL_PACKAGE}.Confirmation",
    GET_ISSUE: f"{PROTOCOL_PACKAGE}.GetIssue",
    GET_ISSUE_RESPONSE: f"{PROTOCOL_PACKAGE}.GetIssueResponse",
}


# Messages
Application, ApplicationSchema = generate_model_schema(
    name="Application",
    handler=f"{PROTOCOL_PACKAGE}.ApplicationHandler",
    msg_type=APPLICATION,
    schema={
        "service_id": fields.Str(required=True),
        "exchange_id": fields.Str(required=True),
        "credential_definition_id": fields.Str(required=True),
        "data_dri": fields.Str(required=True),
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
    schema={"exchange_id": fields.Str(required=True),},
)

GetIssueResponse, GetIssueResponseSchema = generate_model_schema(
    name="GetIssueResponse",
    handler=f"{PROTOCOL_PACKAGE}.GetIssueResponseHandler",
    msg_type=GET_ISSUE_RESPONSE,
    schema={
        "label": fields.Str(required=False),
        "payload": fields.Str(required=False),
        "consent_schema": fields.Str(required=False),
        "service_schema": fields.Str(required=False),
        "exchange_id": fields.Str(required=False),
    },
)
