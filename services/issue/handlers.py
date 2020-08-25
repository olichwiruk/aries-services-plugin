# Acapy
from aries_cloudagent.messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)
from aries_cloudagent.storage.base import BaseStorage
from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.core.plugin_registry import PluginRegistry
from aries_cloudagent.ledger.base import BaseLedger
from aries_cloudagent.issuer.base import BaseIssuer
from aries_cloudagent.protocols.issue_credential.v1_0.manager import CredentialManager
from aries_cloudagent.protocols.connections.v1_0.manager import ConnectionManager


# Records, messages and schemas
from aries_cloudagent.connections.models.connection_record import ConnectionRecord
from aries_cloudagent.storage.record import StorageRecord
from aries_cloudagent.protocols.issue_credential.v1_0.messages.credential_proposal import (
    CredentialProposal,
)
from aries_cloudagent.protocols.issue_credential.v1_0.messages.credential_offer import (
    CredentialOfferSchema,
)
from aries_cloudagent.protocols.issue_credential.v1_0.messages.inner.credential_preview import (
    CredentialPreview,
    CredentialPreviewSchema,
)
from aries_cloudagent.messaging.agent_message import AgentMessage, AgentMessageSchema
from aries_cloudagent.protocols.issue_credential.v1_0.models.credential_exchange import (
    V10CredentialExchange,
    V10CredentialExchangeSchema,
)

# Exceptions
from aries_cloudagent.ledger.error import LedgerError
from aries_cloudagent.ledger.error import BadLedgerRequestError
from aries_cloudagent.issuer.base import IssuerError
from aries_cloudagent.storage.error import StorageDuplicateError, StorageNotFoundError
from aries_cloudagent.protocols.problem_report.v1_0.message import ProblemReport

# Internal
from ..util import generate_model_schema
from .message_types import *
from .models import ServiceIssueRecord
from ..models import ServiceRecord

# External
from asyncio import shield
from marshmallow import fields, Schema
import logging
import hashlib
import uuid
import json

LOGGER = logging.getLogger(__name__)


async def send_confirmation(context, responder, exchange_id, state=None):
    LOGGER.info("send confirmation %s", state)
    confirmation = Confirmation(exchange_id=exchange_id, state=state,)

    confirmation.assign_thread_from(context.message)
    await responder.send_reply(confirmation)


# TODO: use standard problem report?
class ApplicationHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        storage: BaseStorage = await context.inject(BaseStorage)

        LOGGER.info("Application Handler %s", context.message)
        assert isinstance(context.message, Application)

        try:
            service: ServiceRecord = await ServiceRecord.retrieve_by_id(
                context, context.message.service_id
            )
        except StorageNotFoundError:
            await send_confirmation(
                context,
                responder,
                context.message.exchange_id,
                ServiceIssueRecord.ISSUE_SERVICE_NOT_FOUND,
            )
            return

        issue = ServiceIssueRecord(
            state=ServiceIssueRecord.ISSUE_PENDING,
            author=ServiceIssueRecord.AUTHOR_OTHER,
            connection_id=context.connection_record.connection_id,
            exchange_id=context.message.exchange_id,
            service_id=context.message.service_id,
            credential_definition_id=context.message.credential_definition_id,
            issuer_data_dri_cache=context.message.data_dri,
            service_schema=service.service_schema,
            consent_schema=service.consent_schema,
            label=service.label,
        )

        issue_id = await issue.save(context)

        await send_confirmation(
            context,
            responder,
            context.message.exchange_id,
            ServiceIssueRecord.ISSUE_PENDING,
        )

        await responder.send_webhook(
            "verifiable-services",
            {"ServiceIssueRecord": issue.serialize(), "issue_id": issue_id},
        )


class ConfirmationHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        storage: BaseStorage = await context.inject(BaseStorage)

        LOGGER.info("OK Confirmation received %s", context.message)
        assert isinstance(context.message, Confirmation)

        try:
            record: ServiceIssueRecord = await ServiceIssueRecord.retrieve_by_exchange_id_and_connection_id(
                context,
                context.message.exchange_id,
                context.connection_record.connection_id,
            )
        except StorageNotFoundError as err:
            LOGGER.info("ConfirmationHandler error %s", err)
            return

        record.state = context.message.state
        record_id = await record.save(context, reason="Updated issue state")

        await responder.send_webhook(
            "verifiable-services",
            {"state": record.state, "issue_id": record_id, "issue": record.serialize()},
        )


class GetIssueHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        storage: BaseStorage = await context.inject(BaseStorage)

        LOGGER.info("OK GetIssueHandler received %s", context.message)
        assert isinstance(context.message, GetIssue)

        try:
            record: ServiceIssueRecord = await ServiceIssueRecord.retrieve_by_exchange_id_and_connection_id(
                context,
                context.message.exchange_id,
                context.connection_record.connection_id,
            )
        except StorageNotFoundError as err:
            LOGGER.error("GetIssueHandler error %s", err)
            return

        response = GetIssueResponse(
            label=record.label,
            payload=record.payload,
            service_schema=json.dumps(record.service_schema),
            consent_schema=json.dumps(record.consent_schema),
            exchange_id=record.exchange_id,
        )

        response.assign_thread_from(context.message)
        await responder.send_reply(response)


class GetIssueResponseHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        print("OK GetIssueResponseHandler received")
        assert isinstance(context.message, GetIssueResponse)

        try:
            record: ServiceIssueRecord = await ServiceIssueRecord.retrieve_by_exchange_id_and_connection_id(
                context,
                context.message.exchange_id,
                context.connection_record.connection_id,
            )
        except StorageNotFoundError as err:
            LOGGER.error("GetIssueResponseHandler error %s", err)
            return

        if record.label == None:
            record.label = context.message.label
        if record.payload == None:
            record.payload = context.message.payload
        if record.service_schema == None:
            record.service_schema = json.loads(context.message.service_schema)
        if record.consent_schema == None:
            record.consent_schema = json.loads(context.message.consent_schema)
        await record.save(context)

