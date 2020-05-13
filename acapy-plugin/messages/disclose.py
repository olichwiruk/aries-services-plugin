"""Represents a feature discovery disclosure message."""

from typing import Mapping, Sequence

from marshmallow import fields, Schema
from marshmallow.validate import OneOf

from aries_cloudagent.messaging.agent_message import AgentMessage, AgentMessageSchema

from ..message_types import DISCLOSE, PROTOCOL_PACKAGE

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.disclose_handler.DiscloseHandler"


class Disclose(AgentMessage):
    """Represents a feature discovery disclosure, the response to a query message."""

    class Meta:
        """Disclose metadata."""

        handler_class = HANDLER_CLASS
        message_type = DISCLOSE
        schema_class = "DiscloseSchema"

    def __init__(self, *, protocols: str = None, **kwargs):
        """
        Initialize disclose message object.

        Args:
            protocols: A mapping of protocol names to a dictionary of properties
        """
        super(Disclose, self).__init__(**kwargs)
        self.protocols = "hello world"


class DiscloseSchema(AgentMessageSchema):
    """Disclose message schema used in serialization/deserialization."""

    class Meta:
        """DiscloseSchema metadata."""

        model_class = Disclose

    protocols = fields.String(required=True)
