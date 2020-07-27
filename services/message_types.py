from .discovery.message_types import MESSAGE_TYPES as DISCOVERY_MESSAGE_TYPES
from .issue.message_types import MESSAGE_TYPES as ISSUE_MESSAGE_TYPES

# This is the place where you register agent messages, agent message
# should point at the handler that takes care of the agent message,
# URI that identifies the message and package where messages is located

# NOTE: all the message types in sub protocols land in the same dictionary
# so its important that the names wont collide, MESSAGE_TYPES from this
# file is dynamically loaded by acapy


MESSAGE_TYPES = {}
MESSAGE_TYPES.update(DISCOVERY_MESSAGE_TYPES)
MESSAGE_TYPES.update(ISSUE_MESSAGE_TYPES)
