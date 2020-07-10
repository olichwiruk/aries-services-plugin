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
    schema={
        "payload": fields.Str(required=True),
        "cross_planetary_identification_number": fields.Str(required=True),
    },
)

# TODO: how to use webhooks
class RequestHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        storage: BaseStorage = await context.inject(BaseStorage)

        self._logger.debug(
            "SCHEMA_EXCHANGE Request called with context %s, \n\nRESPONDER: %s",
            context,
            responder,
        )
        assert isinstance(context.message, Request)

        state = SchemaExchangeRequestRecord.STATE_REJECTED
        try:
            record = await SchemaExchangeRecord.retrieve_by_id(
                context, context.message.payload
            )
            state = SchemaExchangeRequestRecord.STATE_ACCEPTED
        except StorageNotFoundError:
            response = Response(
                decision="rejected",
                cross_planetary_identification_number=context.message.cross_planetary_identification_number,
                payload="STORAGE NOT FOUND",
            )
            response.assign_thread_from(context.message)
            await responder.send_reply(response)

        request_record = SchemaExchangeRequestRecord(
            payload=context.message.payload,
            author=SchemaExchangeRequestRecord.AUTHOR_OTHER,
            state=state,
            connection_id=context.connection_record.connection_id,
            cross_planetary_identification_number=context.message.cross_planetary_identification_number,
        )

        try:
            request_record_id = await request_record.save(
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
                "hashid": request_record_id,
                "connection_id": context.connection_record.connection_id,
                "payload": record.payload,
                "state": record.state,
                "cross_planetary_identification_number": context.message.cross_planetary_identification_number,
            },
        )

        if state == SchemaExchangeRequestRecord.STATE_ACCEPTED:
            response = Response(
                decision="accepted",
                cross_planetary_identification_number=context.message.cross_planetary_identification_number,
                payload=record.payload,
            )
            response.assign_thread_from(context.message)
            await responder.send_reply(response)


Response, ResponseSchema = generate_model_schema(
    name="Response",
    handler=f"{PROTOCOL_PACKAGE}.ResponseHandler",
    msg_type=RESPONSE,
    schema={
        "decision": fields.Str(required=True),
        "cross_planetary_identification_number": fields.Str(required=True),
        "payload": fields.Str(required=False),
    },
)


class ResponseHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        storage: BaseStorage = await context.inject(BaseStorage)
        self._logger.debug("SCHEMA_EXCHANGE_RESPONSE called with context %s", context)
        assert isinstance(context.message, Response)

        decision = context.message.decision
        payload = context.message.payload
        connection_id = context.connection_record.connection_id
        cross_planetary_identification_number = (
            context.message.cross_planetary_identification_number
        )

        try:
            request_record: SchemaExchangeRequestRecord = await SchemaExchangeRequestRecord.retrieve_by_cross_planetary_identification_number(
                context, cross_planetary_identification_number
            )
        except StorageNotFoundError:
            self._logger.debug("RESPONSE HANDLER RETRIEVE ID ")
            report = ProblemReport(
                explain_ltxt="RequestRecordNotFound", who_retries="none"
            )
            report.assign_thread_from(context.message)
            await responder.send_reply(report)
            return

        request_record.state = decision
        await request_record.save(context)

        hashid = SchemaExchangeRequestRecord.STATE_REJECTED
        if decision == SchemaExchangeRequestRecord.STATE_ACCEPTED:

            self._logger.debug("\nCONNECTION _ACCEPTED\n")
            record: SchemaExchangeRecord = SchemaExchangeRecord(
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
