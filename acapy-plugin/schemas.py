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

PROTOCOL_URL = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/acapy-plugin/1.0"

NEW_SCHEMA = f"{PROTOCOL_URL}/schema"
SEARCH_SCHEMA = f"{PROTOCOL_URL}/search_schema"

PROTOCOL_PACKAGE = "acapy-plugin"
SCHEMAS = f"{PROTOCOL_PACKAGE}.schemas"

MESSAGE_TYPES = {
    NEW_SCHEMA: f"{SCHEMAS}.NewSchemaClass",
    SEARCH_SCHEMA: f"{SCHEMAS}.SearchSchemaClass",
}

NEW_SCHEMA_HANDLER = f"{SCHEMAS}.NewSchemaHandler"
SEARCH_SCHEMA_HANDLER = f"{SCHEMAS}.SearchSchemaHandler"


class NewSchemaClass(AgentMessage):
    class Meta:
        handler_class = NEW_SCHEMA_HANDLER
        message_type = NEW_SCHEMA
        schema_class = "NewSchema"

    def __init__(self, *, payload: str = None, **kwargs):
        super(NewSchemaClass, self).__init__(**kwargs)
        self.payload = payload


class NewSchema(AgentMessageSchema):
    class Meta:
        model_class = NewSchemaClass

    payload = fields.Str(required=False)


class SearchSchemaClass(AgentMessage):
    class Meta:
        handler_class = SEARCH_SCHEMA_HANDLER
        message_type = SEARCH_SCHEMA
        schema_class = "SearchSchema"

    def __init__(self, *, type: str = None, **kwargs):
        super(SearchSchemaClass, self).__init__(**kwargs)
        self.type = type


class SearchSchema(AgentMessageSchema):
    class Meta:
        model_class = SearchSchemaClass

    type = fields.Str(required=False)


class NewSchemaHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        storage: BaseStorage = await context.inject(BaseStorage)

        self._logger.debug("NewSchemaHandler called with context %s", context)
        assert isinstance(context.message, NewSchemaClass)

        schema = StorageRecord(type="schema", value=context.message.payload, tags={})
        await storage.add_record(schema)
        reply = NewSchemaClass(payload=context.message.payload)

        reply.assign_thread_from(context.message)
        await responder.send_reply(reply)


class SearchSchemaHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        storage: BaseStorage = await context.inject(BaseStorage)

        self._logger.debug("SearchSchemaHandler called with context %s", context)
        assert isinstance(context.message, SearchSchemaClass)

        reply = await storage.search_records(
            type_filter=context.message.type
        ).fetch_all()

        reply = SearchSchemaClass(type=reply[0].type)

        # reply.assign_thread_from(context.message)
        await responder.send_reply(reply)
