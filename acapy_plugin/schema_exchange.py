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

# External
from marshmallow import fields
import hashlib
import uuid

# Internal
from .records import SchemaExchangeRecord
from .util import *


PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/schema-exchange/1.0"
PROTOCOL_PACKAGE = "acapy_plugin.schema_exchange"

SCHEMA_EXCHANGE = f"{PROTOCOL_URI}/schema-exchange"
SCHEMA_EXCHANGE_RESPONSE = f"{PROTOCOL_URI}/schema-exchange-response"

MESSAGE_TYPES = {
    SCHEMA_EXCHANGE: f"{PROTOCOL_PACKAGE}.SchemaExchange",
    SCHEMA_EXCHANGE_RESPONSE: f"{PROTOCOL_PACKAGE}.SchemaExchangeResponse",
}

SchemaExchange, SchemaExchangeSchema = generate_model_schema(
    name="SchemaExchange",
    handler=f"{PROTOCOL_PACKAGE}.SchemaExchangeHandler",
    msg_type=SCHEMA_EXCHANGE,
    schema={"payload": fields.Str(required=True)},
)

# Should this be named Receive ? Feels wrong to create a receive class when sending
# something to someone and I dont want class for sending and receiveing so schema exchange for now
# TODO: Figure out how to notify about saved record
class SchemaExchangeHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        storage: BaseStorage = await context.inject(BaseStorage)

        self._logger.debug(
            "SCHEMA_EXCHANGE SchemaExchange called with context %s, \n\nRESPONDER: %s",
            context,
            responder,
        )
        assert isinstance(context.message, SchemaExchange)

        record = SchemaExchangeRecord(
            payload=context.message.payload,
            author=SchemaExchangeRecord.AUTHOR_OTHER,
            state=SchemaExchangeRecord.STATE_PENDING,
            connection_id=context.connection_record.connection_id,
        )

        # Add record to storage
        try:
            hashid = await record.save(
                context, reason="Saved, SchemaExchange from Other agent"
            )
        except StorageDuplicateError:
            report = ProblemReport(explain_ltxt="Duplicate", who_retries="none")
            report.assign_thread_from(context.message)
            await responder.send_reply(report)
            return

        await responder.send_webhook(
            "schema_exchange",
            {
                "hashid": hashid,
                "connection_id": context.connection_record.connection_id,
                "payload": context.message.payload,
                "state": "pending",
            },
        )


SchemaExchangeResponse, SchemaExchangeResponseSchema = generate_model_schema(
    name="SchemaExchangeResponse",
    handler=f"{PROTOCOL_PACKAGE}.SchemaExchangeResponseHandler",
    msg_type=SCHEMA_EXCHANGE,
    schema={
        "decision": fields.Str(required=True),
        "payload": fields.Str(required=False),
    },
)


class SchemaExchangeResponseHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        storage: BaseStorage = await context.inject(BaseStorage)
        decision = context.message.decision
        payload = context.message.payload
        connection_id = context.connection_record.connection_id
        hashid = None

        self._logger.debug("SCHEMA_EXCHANGE_RESPONSE called with context %s", context)
        assert isinstance(context.message, SchemaExchangeResponse)

        # NOTE: Create and save accepted record to storage
        if decision == SchemaExchangeRecord.STATE_ACCEPTED:

            record = SchemaExchangeRecord(
                payload=payload,
                author=SchemaExchangeRecord.AUTHOR_OTHER,
                state=decision,
                connection_id=connection_id,
            )

            try:
                hashid = await record.save(
                    context, reason="Saved, SchemaExchange from Other agent"
                )
            except StorageDuplicateError:
                report = ProblemReport(explain_ltxt="Duplicate", who_retries="none")
                report.assign_thread_from(context.message)
                await responder.send_reply(report)
                return

        await responder.send_webhook(
            "schema_exchange",
            {
                "hashid": hashid,
                "connection_id": connection_id,
                "payload": payload,
                "state": decision,
            },
        )
