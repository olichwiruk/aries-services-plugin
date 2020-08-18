from aries_cloudagent.connections.models.connection_record import ConnectionRecord
from aries_cloudagent.messaging.valid import UUIDFour
from aries_cloudagent.storage.error import StorageNotFoundError, StorageDuplicateError
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

from aries_cloudagent.ledger.error import LedgerError
from aries_cloudagent.ledger.error import BadLedgerRequestError
from aries_cloudagent.ledger.base import BaseLedger
from aries_cloudagent.storage.base import BaseStorage
from aries_cloudagent.issuer.base import IssuerError
from aries_cloudagent.issuer.base import BaseIssuer
from aries_cloudagent.holder.base import BaseHolder, HolderError
from aries_cloudagent.protocols.issue_credential.v1_0.manager import CredentialManager
from aries_cloudagent.protocols.connections.v1_0.manager import ConnectionManager

from aiohttp import web
from aiohttp_apispec import docs, request_schema

from marshmallow import fields, Schema
import logging
import hashlib
import json
from typing import Sequence
from asyncio import shield

from .message_types import Application
from ..discovery.models import *
from .models import ServiceIssueRecord
from ..issue.message_types import *
from .handlers import send_confirmation

LOGGER = logging.getLogger(__name__)


class ApplySchema(Schema):
    service_id = fields.Str(required=True)
    connection_id = fields.Str(required=True)
    payload = fields.Str(required=True)


class ApplyStatusSchema(Schema):
    service_id = fields.Str(required=False)
    connection_id = fields.Str(required=False)
    exchange_id = fields.Str(required=False)


class GetIssueSchema(Schema):
    exchange_id = fields.Str(required=False)
    connection_id = fields.Str(required=False)


class GetIssueSelfSchema(Schema):
    issue_id = fields.Str(required=False)
    connection_id = fields.Str(required=False)
    service_id = fields.Str(required=False)
    label = fields.Str(required=False)
    author = fields.Str(required=False)
    state = fields.Str(required=False)


class ServiceManager:
    """
    Create instance of this class with create_service_manager function

    errors from functions should be handled with this
    except (IssuerError, LedgerError, BadLedgerRequestError) as err:
    """

    def __init__(self, service: ServiceRecord):
        self.service: ServiceRecord = service

    async def init_context(self, context):
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
                        ["consent_schema", "service_schema", "label"],
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
                credential_definition_id, credential_definition = await shield(
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


@docs(
    tags=["Verifiable Services"],
    summary="Apply to a service that connected agent provides, you need a service_id that you can get from service discovery request list",
)
@request_schema(ApplySchema())
async def apply(request: web.BaseRequest):
    context = request.app["request_context"]
    params = await request.json()
    outbound_handler = request.app["outbound_message_router"]

    try:
        connection: ConnectionRecord = await ConnectionRecord.retrieve_by_id(
            context, params["connection_id"]
        )
        services: ServiceDiscoveryRecord = await ServiceDiscoveryRecord.retrieve_by_connection_id(
            context, params["connection_id"]
        )
        print(services)
        # NOTE(Krzosa): query for a service with exact service_id
        service = None
        for query in services.services:
            if query["service_id"] == params["service_id"]:
                service = query
                break
        if service == None:
            raise StorageNotFoundError
    except StorageNotFoundError:
        raise web.HTTPNotFound

    ledger: BaseLedger = await context.inject(BaseLedger)
    issuer: BaseIssuer = await context.inject(BaseIssuer)

    async with ledger:
        schema_id, schema_definition = await shield(
            ledger.create_and_send_schema(
                issuer,
                "consent_schema",
                "1.0",
                ["oca_schema_dri", "oca_schema_namespace", "data_url"],
            )
        )
        LOGGER.info("OK consent schema saved on ledger! %s", schema_id)

    async with ledger:
        credential_definition_id, credential_definition = await shield(
            ledger.create_and_send_credential_definition(
                issuer,
                schema_id,
                signature_type=None,
                tag="consent_schema",
                support_revocation=False,
            )
        )
        LOGGER.info(
            "OK consent_schema CREDENTIAL DEFINITION saved on ledger! %s",
            credential_definition_id,
        )

    print(service)
    credential_exchange_record, credential_offer_message = await _create_free_offer(
        context,
        credential_definition_id,
        params["connection_id"],
        True,
        True,
        {
            "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/issue-credential/1.0/credential-preview",
            "attributes": [
                {
                    "name": "oca_schema_dri",
                    "mime-type": "application/json",
                    "value": service["consent_schema"]["oca_schema_dri"],
                },
                {
                    "name": "oca_schema_namespace",
                    "mime-type": "application/json",
                    "value": service["consent_schema"]["oca_schema_namespace"],
                },
                {
                    "name": "data_url",
                    "mime-type": "application/json",
                    "value": service["consent_schema"]["data_url"],
                },
            ],
        },
    )

    print("credential_exhcagne record", credential_exchange_record)
    print("MESSAGE CRED", credential_offer_message)

    if connection.is_ready:
        await outbound_handler(
            credential_offer_message, connection_id=params["connection_id"]
        )

        record = ServiceIssueRecord(
            connection_id=params["connection_id"],
            state=ServiceIssueRecord.ISSUE_WAITING_FOR_RESPONSE,
            author=ServiceIssueRecord.AUTHOR_SELF,
            service_id=service["service_id"],
            label=service["label"],
            consent_schema=service["consent_schema"],
            service_schema=service["service_schema"],
            payload=params["payload"],
            credential_definition_id=credential_exchange_record.credential_definition_id,
        )

        await record.save(context)

        request = Application(
            service_id=record.service_id,
            exchange_id=record.exchange_id,
            credential_definition_id=credential_exchange_record.credential_definition_id,
        )
        await outbound_handler(request, connection_id=params["connection_id"])
        return web.json_response(request.serialize())

    raise web.HTTPBadGateway


@docs(
    tags=["Verifiable Services"], summary="Get the issue state",
)
@request_schema(ApplyStatusSchema())
async def apply_status(request: web.BaseRequest):
    context = request.app["request_context"]
    params = await request.json()

    try:
        query = await ServiceIssueRecord.query(context, tag_filter=params)
    except StorageNotFoundError:
        raise web.HTTPNotFound

    query = [i.serialize() for i in query]

    return web.json_response(query)


class ProcessApplicationSchema(Schema):
    issue_id = fields.Str(required=True)
    decision = fields.Str(required=True)


# TODO: Connection record, connection ready
class StatusConfirmer:
    def __init__(self, outbound_handler, connection_id, exchange_id):
        self.outbound_handler = outbound_handler
        self.connection_id = connection_id
        self.exchange_id = exchange_id

    async def send_confirmation(self, state):
        confirmation = Confirmation(exchange_id=self.exchange_id, state=state)
        await self.outbound_handler(confirmation, connection_id=self.connection_id)


@docs(
    tags=["Verifiable Services"],
    summary="Decide whether application should be accepted or rejected",
    description="""
    issue_id - first you need to call get_issue_self and search for 
    issues with "pending" state, those should return you issue_id

    decision:
    "accept"
    "reject" 
    """,
)
@request_schema(ProcessApplicationSchema())
async def process_application(request: web.BaseRequest):
    outbound_handler = request.app["outbound_message_router"]
    context = request.app["request_context"]
    params = await request.json()
    REJECTED = ServiceIssueRecord.ISSUE_REJECTED
    LEDGER_ERROR = ServiceIssueRecord.ISSUE_SERVICE_LEDGER_ERROR
    ACCEPTED = ServiceIssueRecord.ISSUE_ACCEPTED

    try:
        issue: ServiceIssueRecord = await ServiceIssueRecord.retrieve_by_id(
            context, params["issue_id"]
        )
        service: ServiceRecord = await ServiceRecord.retrieve_by_id(
            context, issue.service_id
        )
    except StorageNotFoundError:
        raise web.HTTPNotFound

    confirmer = StatusConfirmer(
        outbound_handler, issue.connection_id, issue.exchange_id
    )

    if params["decision"] == "reject":
        issue.state = REJECTED
        await confirmer.send_confirmation(REJECTED)
        return web.json_response(issue.serialize())

    # NOTE(KKrzosa): Search for a consent credential
    holder: BaseHolder = await context.inject(BaseHolder)

    service_namespace = service.consent_schema["oca_schema_namespace"]
    service_dri = service.consent_schema["oca_schema_dri"]
    service_data_url = service.consent_schema["data_url"]

    iterator = 0
    found_credential = None
    credential_list = None
    while credential_list != []:
        credential_list = await holder.get_credentials(
            iterator, iterator + 100, {"cred_def_id": issue.credential_definition_id},
        )

        # NOTE(Krzosa): search through queried credentials chunk for the credential that
        # matches the service credential
        break_the_outer_loop = False
        for credential in credential_list:
            if (
                credential["attrs"]["data_url"] == service_data_url
                and credential["attrs"]["oca_schema_namespace"] == service_namespace
                and credential["attrs"]["oca_schema_dri"] == service_dri
            ):
                found_credential = credential

                # NOTE(KKrzosa): break inner and outer loop
                break_the_outer_loop = True
                break

        # NOTE(KKrzosa): if the record got found -> break the while loop
        if break_the_outer_loop:
            break

        iterator += 100

    if found_credential == None:
        raise web.HTTPNotFound(reason="Credential for consent not found")

    print("CREDENTIAL MEMES")
    print(credential)
    print(credential_list)
    print("\n\n\n\n\n")

    service_manager: ServiceManager = await create_service_manager(context, service)

    try:
        await service_manager.create_schema()
        await service_manager.create_credential_definition()
        (
            credential_exchange_record,
            credential_offer_message,
        ) = await service_manager.create_credential_offer(
            connection_id=issue.connection_id,
            preview_spec={
                "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/issue-credential/1.0/credential-preview",
                "attributes": [
                    {
                        "name": "label",
                        "mime-type": "application/json",
                        "value": service.label,
                    },
                    {
                        "name": "consent_schema",
                        "mime-type": "application/json",
                        "value": json.dumps(service.consent_schema),
                    },
                    {
                        "name": "service_schema",
                        "mime-type": "application/json",
                        "value": json.dumps(service.service_schema),
                    },
                ],
            },
            auto_issue=True,
            auto_remove=False,
        )
    except (LedgerError, IssuerError, BadLedgerRequestError) as err:
        LOGGER.error(
            "credential offer creation error! %s", err,
        )
        issue.state = LEDGER_ERROR
        await confirmer.send_confirmation(LEDGER_ERROR)
        return web.json_response(issue.serialize())

    issue.state = ACCEPTED
    await issue.save(context, reason="Accepted service issue, credential offer created")

    await outbound_handler(credential_offer_message, connection_id=issue.connection_id)
    await confirmer.send_confirmation(ACCEPTED)
    return web.json_response(
        {
            "issue": issue.serialize(),
            "credential_exchange_record": credential_exchange_record.serialize(),
        }
    )


@docs(
    tags=["Verifiable Services"],
    summary="Search for issue by a specified tag",
    description="""
    You don't need to fill any of this, all the filters are optional
    make sure to delete ones you dont use

    STATES: 
    "pending" - not processed yet (not rejected or accepted)
    "no response" - agent didn't respond at all yet
    "service not found"
    "ledger error"
    "cred prep complete"
    "rejected"
    "accepted"

    AUTHORS:
    "self"
    "other"

    This endpoint under the hood calls all the agents that we have 
    uncomplete information about and requests the uncomplete information (payload)
    that information can be retrieved on the next call to get-issue-self
    """,
)
@request_schema(GetIssueSelfSchema())
async def get_issue_self(request: web.BaseRequest):
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]
    params = await request.json()

    try:
        query = await ServiceIssueRecord.query(context, tag_filter=params)
    except StorageNotFoundError:
        raise web.HTTPNotFound

    result = []
    for i in query:
        record: dict = i.serialize()
        # NOTE(Krzosa): serialize additional fields which are not serializable
        # by default
        record.update(
            {
                "issue_id": i._id,
                "label": i.label,
                "payload": i.payload,
                "service_schema": json.dumps(i.service_schema),
                "consent_schema": json.dumps(i.consent_schema),
            }
        )
        result.append(record)

        # NOTE(Krzosa): request additional information from the agent
        # that we had this interaction with
        if record["payload"] == None:
            request = GetIssue(exchange_id=i.exchange_id)
            await outbound_handler(request, connection_id=i.connection_id)

    return web.json_response(result)


@docs(
    tags=["Verifiable Services"], summary="needs a rework",
)
@request_schema(GetIssueSchema())
async def get_issue(request: web.BaseRequest):
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]
    params = await request.json()

    try:
        connection: ConnectionRecord = await ConnectionRecord.retrieve_by_id(
            context, params["connection_id"]
        )
    except StorageNotFoundError:
        raise web.HTTPNotFound

    if connection.is_ready:
        request = GetIssue(exchange_id=params["exchange_id"])
        await outbound_handler(request, connection_id=connection.connection_id)
        return web.json_response(request.serialize())

    raise web.HTTPNotFound
