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
from .models import (
    ServiceRecord,
    ServiceRecordSchema,
    ConsentSchema,
    ServiceSchema,
    ServiceDiscoveryRecord,
)
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

        try:
            record: ServiceDiscoveryRecord = ServiceDiscoveryRecord(
                services=context.message.services, connection_id=connection_id,
            )
            print("\n\nRECORD SAVE\n\n")
            print(record)
            if context.message.services != []:
                assert record.services != []

            await record.save(context)
        except StorageDuplicateError:
            record = await ServiceDiscoveryRecord.retrieve_by_connection_id(
                context, connection_id
            )
            print("\n\RECORD RETRIEVE CONNENCTION _ID\n\n")
            print(record)
            record.services = context.message.services
            await record.save(context)

