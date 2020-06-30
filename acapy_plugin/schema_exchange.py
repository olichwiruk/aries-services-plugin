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


SEND = f"{PROTOCOL_URI}/send"
GET = f"{PROTOCOL_URI}/get"
SEND_RESPONSE = f"{PROTOCOL_URI}/send-response"
SCHEMA_EXCHANGE = f"{PROTOCOL_URI}/schema-exchange"

MESSAGE_TYPES = {
    SEND: f"{PROTOCOL_PACKAGE}.Send",
    GET: f"{PROTOCOL_PACKAGE}.Get",
    SEND_RESPONSE: f"{PROTOCOL_PACKAGE}.SendResponse",
    SCHEMA_EXCHANGE: f"{PROTOCOL_PACKAGE}.SchemaExchange",
}

## Important agent messages


SchemaExchange, SchemaExchangeSchema = generate_model_schema(
    name="SchemaExchange",
    handler=f"{PROTOCOL_PACKAGE}.SchemaExchangeHandler",
    msg_type=SCHEMA_EXCHANGE,
    schema={"payload": fields.Str(required=True), "hashid": fields.Str(required=False)},
)

# Should this be named Receive ? Feels wrong to create a receive class when sending
# something to someone and I dont want class for sending and receiveing so schema exchange for now
# TODO: Figure out how to notify about saved record
class SchemaExchangeHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        storage: BaseStorage = await context.inject(BaseStorage)

        self._logger.debug(
            "SCHEMA_EXCHANGE SchemaExchange called with context %s", context
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
            await record.save(context, reason="Saved, SchemaExchange from Other agent")
        except StorageDuplicateError:
            report = ProblemReport(explain_ltxt="Duplicate", who_retries="none")
            report.assign_thread_from(context.message)
            await responder.send_reply(report)
            return


SendResponse, SendResponseSchema = generate_model_schema(
    name="SendResponse",
    handler=f"{PROTOCOL_PACKAGE}.SendResponseHandler",
    msg_type=SEND_RESPONSE,
    schema={
        "payload": fields.Str(required=True),
        "connection_id": fields.Str(required=True),
        "hashid": fields.Str(required=True),
        "state": fields.Str(required=True),
    },
)


class SendResponseHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        self._logger.debug(
            "SCHEMA_EXCHANGE_SendResponseHandler called with context %s", context
        )
        assert isinstance(context.message, SendResponse)

        # Get connection based on send message -> connection_id
        try:
            connection = await ConnectionRecord.retrieve_by_id(
                context, context.message.connection_id
            )
        except StorageNotFoundError:
            report = ProblemReport(
                explain_ltxt="Connection not found.", who_retries="none"
            )
            report.assign_thread_from(context.message)
            await responder.send_reply(report)
            return

        try:
            record: SchemaExchangeRecord = await SchemaExchangeRecord.retrieve_by_id(
                context, context.message.hashid
            )
        except StorageNotFoundError:
            report = ProblemReport(explain_ltxt="Record not found.", who_retries="none")
            report.assign_thread_from(context.message)
            await responder.send_reply(report)
            return

        self._logger.debug("SendResponseHandler retrieved schema %s", record)

        # Send based on connection id to the peer agent
        message = SchemaExchange(payload=context.message.payload)
        await responder.send(message, connection_id=connection.connection_id)

        # Pack and reply to the admin
        reply = SendResponse(payload=record.payload, hashid=context.message.hashid)
        reply.assign_thread_from(context.message)
        await responder.send_reply(reply)


Send, SendSchema = generate_model_schema(
    name="Send",
    handler=f"{PROTOCOL_PACKAGE}.SendHandler",
    msg_type=SEND,
    schema={
        # request
        "payload": fields.Str(required=True),
        "connection_id": fields.Str(required=True),
        # response
        "hashid": fields.Str(required=False),
    },
)


class SendHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        self._logger.debug(
            "SCHEMA_EXCHANGE SendHandler called with context %s", context
        )
        assert isinstance(context.message, Send)

        # Get connection based on send message -> connection_id
        try:
            connection = await ConnectionRecord.retrieve_by_id(
                context, context.message.connection_id
            )
        except StorageNotFoundError:
            report = ProblemReport(
                explain_ltxt="Connection not found.", who_retries="none"
            )
            report.assign_thread_from(context.message)
            await responder.send_reply(report)
            return

        # Send based on connection id
        message = SchemaExchange(payload=context.message.payload)
        await responder.send(message, connection_id=connection.connection_id)

        # Create record to store localy
        record = SchemaExchangeRecord(
            payload=context.message.payload,
            author="self",
            state=SchemaExchangeRecord.STATE_PENDING,
        )

        # Add record to storage
        try:
            hashid = await record.save(context, reason="Send a SchemaExchange proposal")
        except StorageDuplicateError:
            report = ProblemReport(explain_ltxt="Duplicate", who_retries="none")
            report.assign_thread_from(context.message)
            await responder.send_reply(report)
            return

        # Pack and reply
        reply = Send(payload=record.payload, hashid=hashid)
        reply.assign_thread_from(context.message)
        await responder.send_reply(reply)


Get, GetSchema = generate_model_schema(
    name="Get",
    handler=f"{PROTOCOL_PACKAGE}.GetHandler",
    msg_type=GET,
    schema={
        # request
        "hashid": fields.Str(required=True),
        # response
        "payload": fields.Str(required=False),
    },
)


class GetHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        self._logger.debug("SCHEMA_EXCHANGE GetHandler called with context %s", context)
        assert isinstance(context.message, Get)

        ## Search for record
        try:
            record = await SchemaExchangeRecord.retrieve_by_id(
                context=context, record_id=context.message.hashid
            )
            self._logger.debug("GetHandler SchemaExchangeRecord Query : %s", record)
        except StorageNotFoundError:
            report = ProblemReport(explain_ltxt="RecordNotFound", who_retries="none")
            report.assign_thread_from(context.message)
            await responder.send_reply(report)
            return

        # Pack and reply
        reply = Get(hashid=context.message.hashid, payload=record.value)
        reply.assign_thread_from(context.message)
        await responder.send_reply(reply)

