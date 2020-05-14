from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.core.protocol_registry import ProtocolRegistry

PROTOCOL_URL = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/simplest-protocol/1.0"


async def setup(context: InjectionContext, protocol_registry: ProtocolRegistry = None):
    """Setup the connections plugin."""
    if not protocol_registry:
        protocol_registry = await context.inject(ProtocolRegistry)

    protocol_registry.register_message_types(PROTOCOL_URL)
