from aries_cloudagent.core.protocol_registry import ProtocolRegistry
from aries_cloudagent.config.injection_context import InjectionContext

from .schemas import MESSAGE_TYPES


async def setup(context: InjectionContext):
    protocol_registry = await context.inject(ProtocolRegistry)
    if not protocol_registry:
        protocol_registry = await context.inject(ProtocolRegistry)
    protocol_registry.register_message_types(MESSAGE_TYPES)
