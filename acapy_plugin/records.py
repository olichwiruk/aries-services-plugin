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
import uuid

PROTOCOL_URL = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/acapy-plugin/1.0/records"

RECORDS_ADD = f"{PROTOCOL_URL}/add"
RECORDS_GET = f"{PROTOCOL_URL}/get"

PROTOCOL_PACKAGE = "acapy_plugin"
RECORDS = f"{PROTOCOL_PACKAGE}.records"

MESSAGE_TYPES = {
    RECORDS_ADD: f"{RECORDS}.RecordsAdd",
    RECORDS_GET: f"{RECORDS}.RecordsSearch",
}

RECORDS_ADD_HANDLER = f"{RECORDS}.RecordsAddHandler"
RECORDS_GET_HANDLER = f"{RECORDS}.RecordsGetHandler"


class RecordsAdd(AgentMessage):
    class Meta:
        handler_class = RECORDS_ADD_HANDLER
        message_type = RECORDS_ADD
        schema_class = "RecordsAddSchema"

    def __init__(self, payload: str, record_id: str = None, **kwargs):
        super(RecordsAdd, self).__init__(**kwargs)
        self.payload = payload
        self.record_id = record_id


class RecordsAddSchema(AgentMessageSchema):
    class Meta:
        model_class = RecordsAdd

    payload = fields.Str(required=True)
    record_id = fields.Str(required=False)


class RecordsSearch(AgentMessage):
    class Meta:
        handler_class = RECORDS_GET_HANDLER
        message_type = RECORDS_GET
        schema_class = "RecordsGetSchema"

    def __init__(self, record_id: str, **kwargs):
        super(RecordsSearch, self).__init__(**kwargs)
        self.record_id = record_id


class RecordsGetSchema(AgentMessageSchema):
    class Meta:
        model_class = RecordsSearch

    record_id = fields.Str(required=True)


class RecordsAddHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        storage: BaseStorage = await context.inject(BaseStorage)

        self._logger.debug("RecordsAddHandler called with context %s", context)
        assert isinstance(context.message, RecordsAdd)

        record = StorageRecord(type="OCASchema", value=context.message.payload)
        await storage.add_record(record)

        reply = RecordsAdd(payload=record.value, record_id=record.id)

        reply.assign_thread_from(context.message)
        await responder.send_reply(reply)


class RecordsGetHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        storage: BaseStorage = await context.inject(BaseStorage)

        self._logger.debug("RecordsGetHandler called with context %s", context)
        assert isinstance(context.message, RecordsSearch)

        record = await storage.get_record("OCASchema", context.message.record_id)

        reply = RecordsAdd(record_id=record.id, payload=record.value)

        reply.assign_thread_from(context.message)
        await responder.send_reply(reply)
