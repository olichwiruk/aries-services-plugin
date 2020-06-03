from aries_cloudagent.core.protocol_registry import ProtocolRegistry
from aries_cloudagent.messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)

from ..messages.query import Query


class QueryHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        registry: ProtocolRegistry = await context.inject(ProtocolRegistry)
        reply = Query(comment=context.message.comment)
        reply.assign_thread_from(context.message)
        await responder.send_reply(reply)
