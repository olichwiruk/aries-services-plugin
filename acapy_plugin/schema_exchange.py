from aries_cloudagent.storage.base import BaseStorage
from aries_cloudagent.messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)
from aries_cloudagent.storage.record import StorageRecord
from aries_cloudagent.storage.error import StorageDuplicateError
from aries_cloudagent.core.plugin_registry import PluginRegistry
from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.messaging.agent_message import AgentMessage, AgentMessageSchema

from marshmallow import fields

import hashlib
import uuid

from .message_types import *
from .util import *


PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/schema-exchange/1.0"
PROTOCOL_PACKAGE = "acapy_plugin.schema_exchange"


SEND = f"{PROTOCOL_URI}/send"
GET = f"{PROTOCOL_URI}/get"
# SCHEMA_EXCHANGE = f"{PROTOCOL_URI}/schema-exchange"

MESSAGE_TYPES = {
    SEND: f"{PROTOCOL_PACKAGE}.Send",
    GET: f"{PROTOCOL_PACKAGE}.Get",
    # SCHEMA_EXCHANGE: f"{PROTOCOL_PACKAGE}.SchemaExchange"
}

RECORD_TYPE = "GenericData"

Send, SendSchema = generate_model_schema(
    name="Send",
    handler=f"{PROTOCOL_PACKAGE}.SendHandler",
    msg_type=SEND,
    schema={
        "payload": fields.Str(required=True),
        "hashid": fields.Str(required=False),
    },
)


Get, GetSchema = generate_model_schema(
    name="Get",
    handler=f"{PROTOCOL_PACKAGE}.GetHandler",
    msg_type=GET,
    schema={
        "hashid": fields.Str(required=True),
        "payload": fields.Str(required=False),
    },
)


class SendHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        storage: BaseStorage = await context.inject(BaseStorage)

        self._logger.debug("SCHEMA_EXCHANGE SendHandler called with context %s", context)
        assert isinstance(context.message, Send)

        payloadUTF8 = context.message.payload.encode("UTF-8")
        record_hash = hashlib.sha256(payloadUTF8).hexdigest()

        record = StorageRecord(
            id=record_hash, type=RECORD_TYPE, value=context.message.payload)

        # add record to storage
        try:
            await storage.add_record(record)
        except StorageDuplicateError:
            report = ProblemReport(explain_ltxt="Duplicate", who_retries="none")
            report.assign_thread_from(context.message)
            await responder.send_reply(report)
            return

        reply = Send(payload=record.value, hashid=record.id)
        reply.assign_thread_from(context.message)
        await responder.send_reply(reply)


class GetHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        storage: BaseStorage = await context.inject(BaseStorage)

        self._logger.debug("SCHEMA_EXCHANGE GetHandler called with context %s", context)
        assert isinstance(context.message, Get)

        record = await storage.get_record(RECORD_TYPE, context.message.hashid)

        reply = Get(hashid=record.id, payload=record.value)

        reply.assign_thread_from(context.message)
        await responder.send_reply(reply)
