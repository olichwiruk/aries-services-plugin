from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.core.protocol_registry import ProtocolRegistry

from messages import setup as messages_setup

async def setup(context: InjectionContext):
    protocol_registry = await context.inject(ProtocolRegistry)
    messages_setup(context, protocol_registry)
