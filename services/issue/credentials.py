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

from aries_cloudagent.connections.models.connection_record import ConnectionRecord
from aries_cloudagent.storage.error import StorageNotFoundError, StorageDuplicateError

from aries_cloudagent.ledger.error import LedgerError
from aries_cloudagent.ledger.error import BadLedgerRequestError
from aries_cloudagent.ledger.base import BaseLedger
from aries_cloudagent.storage.base import BaseStorage
from aries_cloudagent.issuer.base import IssuerError
from aries_cloudagent.issuer.base import BaseIssuer
from aries_cloudagent.holder.base import BaseHolder, HolderError
from aries_cloudagent.protocols.issue_credential.v1_0.manager import CredentialManager
from aries_cloudagent.protocols.connections.v1_0.manager import ConnectionManager

from marshmallow import fields, Schema
import logging
import hashlib
import json
import uuid
from typing import Sequence
from asyncio import shield

from .models import *
from .message_types import *
from ..models import *
from .credentials import *

LOGGER = logging.getLogger(__name__)


class ServiceManager:
    """
    Create instance of this class with create_service_manager function like so:
    service_manager: ServiceManager = await create_service_manager(context, service)

    errors from functions should be handled with this
    except (IssuerError, LedgerError, BadLedgerRequestError) as err:
    """

    def __init__(self, service: ServiceRecord):
        self.service: ServiceRecord = service

    async def init_context(self, context):
        """
        this needs to be split from __init__ because init cant be asynchronous
        thats why this class is created with create_service_manager which 
        creates an object and call init_context
        """
        self.context = context
        self.ledger: BaseLedger = await context.inject(BaseLedger)
        self.issuer: BaseIssuer = await context.inject(BaseIssuer)

    async def create_schema(self):
        """
        Register the schema on ledger if not registered
        and save the results in self.service ServiceRecord
        """
        if self.service.ledger_schema_id == None:
            async with self.ledger:
                schema_id, schema_definition = await shield(
                    self.ledger.create_and_send_schema(
                        self.issuer,
                        self.service.label,
                        "1.0",
                        [
                            "data_dri",
                            "oca_schema_dri",
                            "oca_schema_namespace",
                            "service_consent_match_id",
                        ],
                    )
                )
                LOGGER.info("OK Schema saved on ledger! %s", schema_id)

                self.service.ledger_schema_id = schema_id
                await self.service.save(self.context)
        else:
            LOGGER.info(
                "OK SCHEMA already exists for this service! %s",
                self.service.ledger_schema_id,
            )

    async def create_credential_definition(self):
        """
        Register the credential definition on ledger
        Requirements: 
            schema already registered, 
            credential definition not registered yet
        """
        if (
            self.service.ledger_schema_id != None
            and self.service.ledger_credential_definition_id == None
        ):
            async with self.ledger:
                credential_definition_id, credential_definition, novel = await shield(
                    self.ledger.create_and_send_credential_definition(
                        self.issuer,
                        self.service.ledger_schema_id,
                        signature_type=None,
                        tag="Services",
                        support_revocation=False,
                    )
                )
            LOGGER.info(
                "OK CREDENTIAL DEFINITION saved on ledger! %s",
                credential_definition_id,
            )
            self.service.ledger_credential_definition_id = credential_definition_id
            await self.service.save(self.context)
        else:
            LOGGER.info(
                "OK CREDENTIAL DEFINITION already exists for this service! %s",
                self.service.ledger_credential_definition_id,
            )

    async def create_credential_offer(
        self,
        connection_id: str = None,
        preview_spec: dict = None,
        auto_issue: bool = False,
        auto_remove: bool = False,
        comment: str = None,
        trace_message: bool = None,
    ):
        """
        Create a credential offer and related exchange record.
        returns: credential_exchange_record, credential_offer_message
        """

        assert (
            self.service.ledger_credential_definition_id
        ), "self.service.ledger_credential_definition_id is required"
        if auto_issue and not preview_spec:
            assert (
                False
            ), "If auto_issue is set then credential_preview must be provided"

        if preview_spec:
            credential_preview = CredentialPreview.deserialize(preview_spec)
            credential_proposal = CredentialProposal(
                comment=comment,
                credential_proposal=credential_preview,
                cred_def_id=self.service.ledger_credential_definition_id,
            )
            credential_proposal.assign_trace_decorator(
                self.context.settings, trace_message,
            )
            credential_proposal_dict = credential_proposal.serialize()
        else:
            credential_proposal_dict = None

        credential_exchange_record = V10CredentialExchange(
            connection_id=connection_id,
            initiator=V10CredentialExchange.INITIATOR_SELF,
            credential_definition_id=self.service.ledger_credential_definition_id,
            credential_proposal_dict=credential_proposal_dict,
            auto_issue=auto_issue,
            auto_remove=auto_remove,
            trace=trace_message,
        )

        credential_manager = CredentialManager(self.context)

        (
            credential_exchange_record,
            credential_offer_message,
        ) = await credential_manager.create_offer(
            credential_exchange_record, comment=comment
        )

        LOGGER.info("Credential offer created")
        return credential_exchange_record, credential_offer_message


async def create_service_manager(context, service):
    manager = ServiceManager(service)
    await manager.init_context(context)

    return manager


async def create_consent_credential_offer(
    context,
    cred_def_id: str,
    connection_id: str = None,
    consent_schema=None,
    auto_issue: bool = False,
    auto_remove: bool = False,
    comment: str = None,
    trace_msg: bool = None,
):
    """Create a credential offer and related exchange record."""

    service_consent_match_id = str(uuid.uuid4())

    preview_spec: dict = {
        "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/issue-credential/1.0/credential-preview",
        "attributes": [
            {
                "name": "oca_schema_dri",
                "mime-type": "application/json",
                "value": consent_schema["oca_schema_dri"],
            },
            {
                "name": "oca_schema_namespace",
                "mime-type": "application/json",
                "value": consent_schema["oca_schema_namespace"],
            },
            {
                "name": "data_dri",
                "mime-type": "application/json",
                "value": consent_schema["data_dri"],
            },
            {
                "name": "service_consent_match_id",
                "mime-type": "application/json",
                "value": service_consent_match_id,
            },
        ],
    }

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

    return (
        credential_exchange_record,
        credential_offer_message,
        service_consent_match_id,
    )

