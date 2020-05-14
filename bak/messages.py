from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.core.protocol_registry import ProtocolRegistry
from aries_cloudagent.messaging.agent_message import AgentMessage, AgentMessageSchema
from aries_cloudagent.messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)

from marshmallow import fields

PROTOCOL = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/acapy-plugin/1.0"

DISCLOSE = f"{PROTOCOL}/disclose"
QUERY = f"{PROTOCOL}/query"

PROTOCOL_PACKAGE = "acapy-plugin.messages"

MESSAGE_TYPES = {
    DISCLOSE: f"{PROTOCOL_PACKAGE}.Disclose",
    QUERY: f"{PROTOCOL_PACKAGE}.Query",
}


async def setup(context: InjectionContext, protocol_registry: ProtocolRegistry = None):
    if not protocol_registry:
        protocol_registry = await context.inject(ProtocolRegistry)

    protocol_registry.register_message_types(MESSAGE_TYPES)


class Disclose(AgentMessage):
    class Meta:
        handler_class = f"{PROTOCOL_PACKAGE}.DiscloseHandler"
        message_type = DISCLOSE
        schema_class = "DiscloseSchema"

    def __init__(self, *, protocols: str = None, **kwargs):
        super(Disclose, self).__init__(**kwargs)
        self.protocols = "hello world"


class DiscloseSchema(AgentMessageSchema):
    class Meta:
        model_class = Disclose

    protocols = fields.String(required=True)


class DiscloseHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        self._logger.debug("DiscloseHandler called with context %s", context)
        assert isinstance(context.message, Disclose)

        print("Received protocols:\n{}".format(context.message.protocols))


class Query(AgentMessage):
    class Meta:
        handler_class = f"{PROTOCOL_PACKAGE}.QueryHandler"
        message_type = QUERY
        schema_class = "QuerySchema"

    def __init__(self, *, query: str = None, comment: str = None, **kwargs):
        super(Query, self).__init__(**kwargs)
        self.query = query
        self.comment = comment


class QuerySchema(AgentMessageSchema):
    class Meta:
        model_class = Query

    query = fields.Str(required=False)
    comment = fields.Str(required=False)


class QueryHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        self._logger.debug("QueryHandler called with context %s", context)
        assert isinstance(context.message, Query)

        registry: ProtocolRegistry = await context.inject(ProtocolRegistry)
        result = await registry.prepare_disclosed(context, context.message.query)
        reply = Disclose(protocols=result)
        reply.assign_thread_from(context.message)
        await responder.send_reply(reply)
