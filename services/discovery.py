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
from .records import ServiceRecord, ConsentSchema, ServiceSchema
from .message_types import (
    PROTOCOL_PACKAGE_DISCOVERY as PROTOCOL_PACKAGE,
    DISCOVERY,
    DISCOVERY_RESPONSE,
)
from .util import generate_model_schema

# External
from marshmallow import fields
import hashlib
import uuid


Discovery, DiscoverySchema = generate_model_schema(
    name="Discovery",
    handler=f"{PROTOCOL_PACKAGE}.DiscoveryHandler",
    msg_type=DISCOVERY,
    schema={},
)


class DiscoveryResponse(AgentMessage):
    class Meta:
        handler_class = f"{PROTOCOL_PACKAGE}.DiscoveryResponseHandler"
        message_type = DISCOVERY_RESPONSE
        schema_class = "DiscoveryResponseSchema"

    def __init__(self, *, services: list = None, **kwargs):
        super(DiscoveryResponse, self).__init__(**kwargs)
        self.services = services if services else []


class DiscoveryResponseSchema(AgentMessageSchema):
    """DiscoveryResponse message schema used in serialization/deserialization."""

    class Meta:
        model_class = DiscoveryResponse

    protocols = fields.List(fields.Str(required=False), required=False,)


class DiscoveryHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        storage: BaseStorage = await context.inject(BaseStorage)

        self._logger.debug(
            "SERVICES DISCOVERY %s, ", context, responder,
        )
        assert isinstance(context.message, Discovery)

        query = await ServiceRecord().query(context)

        # create a list of serialized(in json format / dict format) records
        query_serialized = [record.serialize() for record in query]

        response = DiscoveryResponse(services=query_serialized)
        response.assign_thread_from(context.message)
        await responder.send_reply(response)


class DiscoveryResponseHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        storage: BaseStorage = await context.inject(BaseStorage)
        self._logger.debug(
            "SERVICES DISCOVERY RESPONSE %s, ", context, responder,
        )
        assert isinstance(context.message, DiscoveryResponse)

        record = StorageRecord(
            "ServiceDiscovery",
            context.message.services,
            tags={"connection_id": context.connection_record.connection_id},
        )
        storage.add_record(record)
