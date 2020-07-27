# Acapy
from aries_cloudagent.messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)
from aries_cloudagent.storage.base import BaseStorage
from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.core.plugin_registry import PluginRegistry
from aries_cloudagent.protocols.connections.v1_0.manager import ConnectionManager

# Records, messages and schemas
from aries_cloudagent.messaging.agent_message import AgentMessage, AgentMessageSchema
from aries_cloudagent.connections.models.connection_record import ConnectionRecord
from aries_cloudagent.storage.record import StorageRecord

# Exceptions
from aries_cloudagent.storage.error import StorageDuplicateError, StorageNotFoundError
from aries_cloudagent.protocols.problem_report.v1_0.message import ProblemReport

# Internal
from ..util import generate_model_schema
from .message_types import *
from .models import ServiceIssueRecord

# External
from marshmallow import fields, Schema
import hashlib
import uuid
import json


async def send_confirmation(context, responder, record):
    confirmation = Confirmation(
        exchange_id=record.exchange_id,
        service_schema=record.service_schema,
        consent_schema=record.consent_schema,
        state=record.state,
    )

    confirmation.assign_thread_from(context.message)
    await responder.send_reply(confirmation)


class ApplicationHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        storage: BaseStorage = await context.inject(BaseStorage)

        print("APPLICATION HANDLER")
        print(context.message)
        assert isinstance(context.message, Application)

        record = ServiceIssueRecord(
            state=ServiceIssueRecord.ISSUE_PENDING,
            service_schema=context.message.service_schema,
            consent_schema=context.message.consent_schema,
            connection_id=context.connection_record.connection_id,
        )

        await send_confirmation(record, responder, context)

        # TODO: Some kind of decision mechanism

        record.state = ServiceIssueRecord.ISSUE_ACCEPTED
        record.save(context)

        await send_confirmation(record, responder, context)


class ConfirmationHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        storage: BaseStorage = await context.inject(BaseStorage)

        print("CONFIRMATION:\n %s", context.message)
        assert isinstance(context.message, Confirmation)

        try:
            record = ServiceIssueRecord.retrieve_by_exchange_id(
                context, context.message.exchange_id
            )
        except StorageNotFoundError:
            record = ServiceIssueRecord(
                state=context.message.state,
                service_schema=context.message.service_schema,
                consent_schema=context.message.consent_schema,
                connection_id=context.connection_record.connection_id,
                exchange_id=context.message.exchange_id,
            )

        record.state = context.message.state

        await record.save(context)
