from .discovery.message_types import MESSAGE_TYPES as DISCOVERY_MESSAGE_TYPES

# from .issue.message_types import MESSAGE_TYPES as ISSUE_MESSAGE_TYPES


# NOTE: all the message types in sub protocols land in the same dictionary
# so its important that the names wont collide
MESSAGE_TYPES = {}
MESSAGE_TYPES.update(DISCOVERY_MESSAGE_TYPES)
# MESSAGE_TYPES.update(ISSUE_MESSAGE_TYPES)
