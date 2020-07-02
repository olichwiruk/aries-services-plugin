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
from .records import SchemaExchangeRecord, SchemaExchangeRequestRecord
from .util import *
from .message_types import *

Request, RequestSchema = generate_model_schema(
    name="Request",
    handler=f"{PROTOCOL_PACKAGE}.RequestHandler",
    msg_type=REQUEST,
    schema={"payload": fields.Str(required=True)},
)

# TODO: Figure out how to handle web hook
class RequestHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        storage: BaseStorage = await context.inject(BaseStorage)

        self._logger.debug(
            "SCHEMA_EXCHANGE Request called with context %s, \n\nRESPONDER: %s",
            context,
            responder,
        )
        assert isinstance(context.message, Request)

        record = SchemaExchangeRequestRecord(
            payload=context.message.payload,
            author=SchemaExchangeRequestRecord.AUTHOR_OTHER,
            state=SchemaExchangeRequestRecord.STATE_PENDING,
            connection_id=context.connection_record.connection_id,
        )

        try:
            record_id = await record.save(
                context, reason="Saved, Request from Other agent"
            )
        except StorageNotFoundError:
            report = ProblemReport(explain_ltxt="StorageNotFound", who_retries="none")
            report.assign_thread_from(context.message)
            await responder.send_reply(report)
            return

        await responder.send_webhook(
            "schema_exchange",
            {
                "id": record_id,
                "hashid": record.hashid,
                "connection_id": context.connection_record.connection_id,
                "payload": record.payload,
                "state": record.state,
            },
        )


Response, ResponseSchema = generate_model_schema(
    name="Response",
    handler=f"{PROTOCOL_PACKAGE}.ResponseHandler",
    msg_type=RESPONSE,
    schema={
        "decision": fields.Str(required=True),
        "payload": fields.Str(required=False),
    },
)


class ResponseHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        storage: BaseStorage = await context.inject(BaseStorage)

        decision = context.message.decision
        payload = context.message.payload
        connection_id = context.connection_record.connection_id
        hashid = None

        self._logger.debug("SCHEMA_EXCHANGE_RESPONSE called with context %s", context)
        assert isinstance(context.message, Response)

        # NOTE: Create and save accepted record to storage
        if decision == SchemaExchangeRecord.STATE_ACCEPTED:
            self._logger.debug("\nState: Accepted")
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
