# Acapy
from aries_cloudagent.messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)
from aries_cloudagent.storage.base import BaseStorage
from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.core.plugin_registry import PluginRegistry
from aries_cloudagent.protocols.connections.v1_0.manager import ConnectionManager

# Records, messages and schemas
from aries_cloudagent.messaging.agent_message import AgentMessage, AgentMessageSchema
from aries_cloudagent.connections.models.connection_record import ConnectionRecord
from aries_cloudagent.storage.record import StorageRecord

# Exceptions
from aries_cloudagent.storage.error import StorageDuplicateError, StorageNotFoundError
from aries_cloudagent.protocols.problem_report.v1_0.message import ProblemReport

# Internal
from .records import (
    ServiceRecord,
    ServiceRecordSchema,
    ConsentSchema,
    ServiceSchema,
    ServiceDiscoveryRecord,
)
from .message_types import PROTOCOL_URI
from .util import generate_model_schema

# External
from marshmallow import fields, Schema
import hashlib
import uuid
import json

PROTOCOL_PACKAGE = "services.issue_credential_consentual"
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


class ApplicationHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        storage: BaseStorage = await context.inject(BaseStorage)

        print(context.message)
        assert isinstance(context.message, Application)
