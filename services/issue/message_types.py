from ..message_types import PROTOCOL_URI

PROTOCOL_PACKAGE = "services.issue.issue_credential_consentual"
APPLICATION = f"{PROTOCOL_URI}/application"
MESSAGE_TYPES = {APPLICATION: f"{PROTOCOL_PACKAGE}.Application"}

Application, ApplicationSchema = generate_model_schema(
    name="Application",
    handler=f"{PROTOCOL_PACKAGE}.ApplicationHandler",
    msg_type=APPLICATION,
    schema={
        "label": fields.Str(required=True),
        "service_schema": fields.Nested(ServiceSchema()),
        "consent_schema": fields.Nested(ConsentSchema()),
    },
)
