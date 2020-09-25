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
from ..models import *
from .message_types import *
from ..util import generate_model_schema

# External
from marshmallow import fields, Schema
import hashlib
import uuid
import json


class DiscoveryHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        storage: BaseStorage = await context.inject(BaseStorage)

        self._logger.debug("SERVICES DISCOVERY %s, ", context)
        assert isinstance(context.message, Discovery)

        query = await ServiceRecord().query(context)

        records = []
        for service in query:
            record = DiscoveryServiceSchema()
            record = record.dump(
                {
                    "service_schema": service.service_schema,
                    "consent_schema": service.consent_schema,
                    "service_id": service._id,
                    "label": service.label,
                }
            )
            records.append(record)

        response = DiscoveryResponse(services=records)
        response.assign_thread_from(context.message)
        await responder.send_reply(response)


class DiscoveryResponseHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        self._logger.debug("SERVICES DISCOVERY RESPONSE %s, ", context)
        assert isinstance(context.message, DiscoveryResponse)

        connection_id = context.connection_record.connection_id

        await responder.send_webhook(
            "verifiable-services/request-service-list",
            {"services": json.dumps(context.message.services)},
        )


"""
DEBUG
"""


class DEBUGServiceDiscoveryRecord(BaseRecord):
    RECORD_ID_NAME = "record_id"
    RECORD_TYPE = "DEBUGservice_discovery"

    class Meta:
        schema_class = "DEBUGServiceDiscoveryRecordSchema"

    def __init__(
        self,
        *,
        services=None,
        connection_id: str = None,
        state: str = None,
        record_id: str = None,
        **keywordArgs,
    ):
        super().__init__(record_id, state, **keywordArgs)
        self.services = services
        self.connection_id = connection_id

    @property
    def record_value(self) -> dict:
        """Accessor to for the JSON record value properties"""
        return {prop: getattr(self, prop) for prop in ("services", "connection_id")}

    @property
    def record_tags(self) -> dict:
        """Get tags for record, 
            NOTE: relevent when filtering by tags"""
        return {
            "connection_id": self.connection_id,
        }

    @classmethod
    async def retrieve_by_connection_id(
        cls, context: InjectionContext, connection_id: str
    ):
        return await cls.retrieve_by_tag_filter(
            context, {"connection_id": connection_id},
        )


class DEBUGServiceDiscoveryRecordSchema(BaseRecordSchema):
    class Meta:
        model_class = "DEBUGServiceDiscoveryRecord"

    services = fields.List(fields.Nested(ServiceRecordSchema()))
    connection_id = fields.Str()


class DEBUGDiscoveryHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        storage: BaseStorage = await context.inject(BaseStorage, )

        print("DEBUG SERVICES DISCOVERY %s, ", context)
        assert isinstance(context.message, DEBUGDiscovery)

        query = await ServiceRecord().query(context)

        records = []
        for service in query:
            record = DiscoveryServiceSchema()
            record = record.dump(
                {
                    "service_schema": service.service_schema,
                    "consent_schema": service.consent_schema,
                    "service_id": service._id,
                    "label": service.label,
                }
            )
            records.append(record)

        response = DEBUGDiscoveryResponse(services=records)
        response.assign_thread_from(context.message)
        await responder.send_reply(response)


class DEBUGDiscoveryResponseHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        print("DEBUG SERVICES DISCOVERY RESPONSE %s, ", context)
        assert isinstance(context.message, DEBUGDiscoveryResponse)

        connection_id = context.connection_record.connection_id

        try:
            record = await DEBUGServiceDiscoveryRecord.retrieve_by_connection_id(
                context, connection_id
            )
            record.services = context.message.services
        except StorageNotFoundError:
            record: DEBUGServiceDiscoveryRecord = DEBUGServiceDiscoveryRecord(
                services=context.message.services, connection_id=connection_id,
            )

        if context.message.services != []:
            assert record.services != []
        await record.save(context)
