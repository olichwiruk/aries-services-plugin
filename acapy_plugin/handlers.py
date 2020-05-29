from aries_cloudagent.storage.base import BaseStorage
from aries_cloudagent.messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)
from aries_cloudagent.storage.record import StorageRecord
from aries_cloudagent.core.plugin_registry import PluginRegistry
from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.messaging.agent_message import AgentMessage, AgentMessageSchema

from marshmallow import fields
import hashlib
import uuid
from .message_types import *
from .messages import *
from .util import *


RECORD_TYPE = "GenericData"


class RecordsAddHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        storage: BaseStorage = await context.inject(BaseStorage)

        self._logger.debug("RecordsAddHandler called with context %s", context)
        assert isinstance(context.message, RecordsAdd)

        payloadUTF8 = context.message.payload.encode("UTF-8")
        record_hash = hashlib.sha256(payloadUTF8).hexdigest()

        record = StorageRecord(
            id=record_hash, type=RECORD_TYPE, value=context.message.payload
        )
        await storage.add_record(record)

        reply = RecordsAdd(payload=record.value, hashid=record.id)

        reply.assign_thread_from(context.message)
        await responder.send_reply(reply)


class RecordsGetHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        storage: BaseStorage = await context.inject(BaseStorage)

        self._logger.debug("RecordsGetHandler called with context %s", context)
        assert isinstance(context.message, RecordsGet)

        record = await storage.get_record(RECORD_TYPE, context.message.hashid)

        reply = RecordsGet(hashid=record.id, payload=record.value)

        reply.assign_thread_from(context.message)
        await responder.send_reply(reply)


# RecordsList, RecordsListSchema = generate_model_schema(
#     name="RecordsList",
#     handler=RECORDS_GET_HANDLER,
#     msg_type=RECORDS_GET,
#     schema = fields.List(
#         fields.Nested(RecordsAddSchema),
#         required=False,
#         allow_none=True)
#     )

# class RecordsListHandler(BaseHandler):
#     async def handle(self, context: RequestContext, responder: BaseResponder):
#         storage: BaseStorage = await context.inject(BaseStorage)

#         self._logger.debug("RecordsListHandler called with context %s", context)
#         assert isinstance(context.message, RecordsGet)

#         records = await storage.search_records(type_filter="GenericData")

#         reply = RecordsGet(hashid=record.id, payload=record.value)

#         reply.assign_thread_from(context.message)
#         await responder.send_reply(reply)
