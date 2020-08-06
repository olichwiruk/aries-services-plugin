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
from aries_cloudagent.connections.models.connection_record import ConnectionRecord
from aries_cloudagent.storage.record import StorageRecord
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
from ..discovery.models import ServiceRecord

# External
from asyncio import shield
from marshmallow import fields, Schema
import logging
import hashlib
import uuid
import json

LOGGER = logging.getLogger(__name__)


async def _create_free_offer(
    context,
    cred_def_id: str,
    connection_id: str = None,
    auto_issue: bool = False,
    auto_remove: bool = False,
    preview_spec: dict = None,
    comment: str = None,
    trace_msg: bool = None,
):
    """Create a credential offer and related exchange record."""

    assert cred_def_id, "cred_def_id is required"
    if auto_issue and not preview_spec:
        assert False, "If auto_issue is set then credential_preview must be provided"

    if preview_spec:
        credential_preview = CredentialPreview.deserialize(preview_spec)
        credential_proposal = CredentialProposal(
            comment=comment,
            credential_proposal=credential_preview,
            cred_def_id=cred_def_id,
        )
        credential_proposal.assign_trace_decorator(
            context.settings, trace_msg,
        )
        credential_proposal_dict = credential_proposal.serialize()
    else:
        credential_proposal_dict = None

    credential_exchange_record = V10CredentialExchange(
        connection_id=connection_id,
        initiator=V10CredentialExchange.INITIATOR_SELF,
        credential_definition_id=cred_def_id,
        credential_proposal_dict=credential_proposal_dict,
        auto_issue=auto_issue,
        auto_remove=auto_remove,
        trace=trace_msg,
    )

    credential_manager = CredentialManager(context)

    (
        credential_exchange_record,
        credential_offer_message,
    ) = await credential_manager.create_offer(
        credential_exchange_record, comment=comment
    )
    return credential_exchange_record, credential_offer_message


async def send_confirmation_raw(context, responder, exchange_id, state=None):
    LOGGER.info("send confirmation %s", state)
    confirmation = Confirmation(exchange_id=exchange_id, state=state,)

    confirmation.assign_thread_from(context.message)
    await responder.send_reply(confirmation)


async def send_confirmation(context, responder, record: ServiceIssueRecord, state=None):
    if state != None:
        record.state = state
    await send_confirmation_raw(context, responder, record.exchange_id, record.state)


# TODO: use standard problem report?
class ApplicationHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        storage: BaseStorage = await context.inject(BaseStorage)

        LOGGER.info("Application Handler %s", context.message)
        assert isinstance(context.message, Application)

        try:
            service: ServiceRecord = await ServiceRecord().retrieve_by_id(
                context, context.message.service_id
            )
        except StorageNotFoundError:
            await send_confirmation_raw(
                context,
                responder,
                context.message.exchange_id,
                ServiceIssueRecord.ISSUE_SERVICE_NOT_FOUND,
            )
            return

        record = ServiceIssueRecord(
            state=ServiceIssueRecord.ISSUE_PENDING,
            author=ServiceIssueRecord.AUTHOR_OTHER,
            connection_id=context.connection_record.connection_id,
            exchange_id=context.message.exchange_id,
            service_id=context.message.service_id,
            label=service.label,
        )

        await send_confirmation(context, responder, record)

        ledger: BaseLedger = await context.inject(BaseLedger)
        issuer: BaseIssuer = await context.inject(BaseIssuer)

        # NOTE(Krzosa): Register the schema on ledger if not registered
        # and save the results in ServiceRecord
        if service.ledger_schema_id == None:
            async with ledger:
                try:
                    schema_id, schema_definition = await shield(
                        ledger.create_and_send_schema(
                            issuer,
                            service.label,
                            "1.0",
                            ["consent_schema", "service_schema", "label"],
                        )
                    )
                    LOGGER.info("OK Schema saved on ledger! %s", schema_id)

                    service.ledger_schema_id = schema_id
                    await service.save(context)
                except (IssuerError, LedgerError) as err:
                    LOGGER.error("SCHEMA failed to save on LEDGER %s", err)
                    await send_confirmation(
                        context,
                        responder,
                        record,
                        ServiceIssueRecord.ISSUE_SERVICE_LEDGER_ERROR,
                    )
                    return
        else:
            LOGGER.info(
                "OK SCHEMA already exists for this service! %s",
                service.ledger_schema_id,
            )

        # NOTE(Krzosa): Register the credential definition on ledger if not registered
        # and save the results in ServiceRecord
        if (
            service.ledger_schema_id != None
            and service.ledger_credential_definition_id == None
        ):
            try:
                async with ledger:
                    credential_definition_id, credential_definition = await shield(
                        ledger.create_and_send_credential_definition(
                            issuer,
                            service.ledger_schema_id,
                            signature_type=None,
                            tag="Services",
                            support_revocation=False,
                        )
                    )
                LOGGER.info(
                    "OK CREDENTIAL DEFINITION saved on ledger! %s",
                    credential_definition_id,
                )
                service.ledger_credential_definition_id = credential_definition_id
                await service.save(context)

            except (LedgerError, IssuerError, BadLedgerRequestError) as err:
                LOGGER.error(
                    "CREDENTIAL DEFINITION failed to create on ledger! %s", err,
                )
                await send_confirmation(
                    context,
                    responder,
                    record,
                    ServiceIssueRecord.ISSUE_SERVICE_LEDGER_ERROR,
                )
                return
        else:
            LOGGER.info(
                "OK CREDENTIAL DEFINITION already exists for this service! %s",
                service.ledger_credential_definition_id,
            )

        await send_confirmation(
            context,
            responder,
            record,
            ServiceIssueRecord.ISSUE_CREDENTIAL_DEFINITION_PREPARATION_COMPLETE,
        )

        # NOTE(Krzosa): Create credential
        credential_exchange_record, credential_offer_message = await _create_free_offer(
            context,
            service.ledger_credential_definition_id,
            context.connection_record.connection_id,
            False,
            False,
            {
                "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/issue-credential/1.0/credential-preview",
                "attributes": [
                    {
                        "name": "label",
                        "mime-type": "application/json",
                        "value": "string",
                    },
                    {
                        "name": "consent_schema",
                        "mime-type": "application/json",
                        "value": "string",
                    },
                    {
                        "name": "service_schema",
                        "mime-type": "application/json",
                        "value": "string",
                    },
                ],
            },
        )
        LOGGER.info("OK CREDENTIAL created! %s", credential_exchange_record)

        await responder.send_reply(credential_offer_message)
        record.state = ServiceIssueRecord.ISSUE_ACCEPTED
        await record.save(context)

        await send_confirmation(context, responder, record)
        LOGGER.info("OK Application protocol end")


class ConfirmationHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        storage: BaseStorage = await context.inject(BaseStorage)

        LOGGER.info("OK Confirmation received %s", context.message)
        assert isinstance(context.message, Confirmation)

        try:
            record = await ServiceIssueRecord.retrieve_by_exchange_id_and_connection_id(
                context,
                context.message.exchange_id,
                context.connection_record.connection_id,
            )
        except StorageNotFoundError as err:
            LOGGER.info("ConfirmationHandler error %s", err)
            return

        record.state = context.message.state
        await record.save(context, reason="Updated issue state")
