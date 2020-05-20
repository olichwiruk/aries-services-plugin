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

PROTOCOL_URL = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/acapy-plugin/1.0"

NEW_SCHEMA = f"{PROTOCOL_URL}/schema"
SEARCH_SCHEMA = f"{PROTOCOL_URL}/search_schema"

PROTOCOL_PACKAGE = "acapy_plugin"
SCHEMAS = f"{PROTOCOL_PACKAGE}.schemas"

MESSAGE_TYPES = {
    NEW_SCHEMA: f"{SCHEMAS}.NewSchemaMessage",
    SEARCH_SCHEMA: f"{SCHEMAS}.SearchSchemaMessage",
}

NEW_SCHEMA_HANDLER = f"{SCHEMAS}.NewSchemaHandler"
SEARCH_SCHEMA_HANDLER = f"{SCHEMAS}.SearchSchemaHandler"


class NewSchemaMessage(AgentMessage):
    class Meta:
        handler_class = NEW_SCHEMA_HANDLER
        message_type = NEW_SCHEMA
        schema_class = "NewSchema"

    def __init__(self, payload: str, schema_id: str = None, **kwargs):
        super(NewSchemaMessage, self).__init__(**kwargs)
        self.payload = payload
        self.schema_id = schema_id


class NewSchema(AgentMessageSchema):
    class Meta:
        model_class = NewSchemaMessage

    payload = fields.Str(required=True)
    schema_id = fields.Str(required=False)


class SearchSchemaMessage(AgentMessage):
    class Meta:
        handler_class = SEARCH_SCHEMA_HANDLER
        message_type = SEARCH_SCHEMA
        schema_class = "SearchSchema"

    def __init__(self, schema_id: str, **kwargs):
        super(SearchSchemaMessage, self).__init__(**kwargs)
        self.schema_id = schema_id


class SearchSchema(AgentMessageSchema):
    class Meta:
        model_class = SearchSchemaMessage

    schema_id = fields.Str(required=True)


class NewSchemaHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        storage: BaseStorage = await context.inject(BaseStorage)

        self._logger.debug("NewSchemaHandler called with context %s", context)
        assert isinstance(context.message, NewSchemaMessage)

        record = StorageRecord(type="OCASchema", value=context.message.payload)
        await storage.add_record(record)

        reply = NewSchemaMessage(payload=record.value, schema_id=record.id)

        reply.assign_thread_from(context.message)
        await responder.send_reply(reply)


class SearchSchemaHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        storage: BaseStorage = await context.inject(BaseStorage)

        self._logger.debug("SearchSchemaHandler called with context %s", context)
        assert isinstance(context.message, SearchSchemaMessage)

        record = await storage.get_record("OCASchema", context.message.schema_id)

        reply = NewSchemaMessage(schema_id=record.id, payload=record.value)

        reply.assign_thread_from(context.message)
        await responder.send_reply(reply)
