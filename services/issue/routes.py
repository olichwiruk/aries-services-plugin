from aries_cloudagent.connections.models.connection_record import ConnectionRecord
from aries_cloudagent.messaging.valid import UUIDFour
from aries_cloudagent.storage.error import StorageNotFoundError, StorageDuplicateError

from aries_cloudagent.ledger.error import LedgerError
from aries_cloudagent.ledger.error import BadLedgerRequestError
from aries_cloudagent.ledger.base import BaseLedger
from aries_cloudagent.storage.base import BaseStorage
from aries_cloudagent.issuer.base import BaseIssuer, IssuerError
from aries_cloudagent.holder.base import BaseHolder, HolderError

from aiohttp import web
from aiohttp_apispec import docs, request_schema

from marshmallow import fields, Schema
import logging
import hashlib
import json
from typing import Sequence
from asyncio import shield

from .models import *
from .message_types import *
from ..models import *
from .credentials import *
from ..discovery.message_types import DiscoveryServiceSchema

LOGGER = logging.getLogger(__name__)


class ApplySchema(Schema):
    connection_id = fields.Str(required=True)
    payload = fields.Str(required=True)
    service = fields.Nested(DiscoveryServiceSchema())


class ApplyStatusSchema(Schema):
    service_id = fields.Str(required=False)
    connection_id = fields.Str(required=False)
    exchange_id = fields.Str(required=False)


class GetCredentialDataSchema(Schema):
    data_dri = fields.Str(required=False)


class GetIssueSchema(Schema):
    exchange_id = fields.Str(required=False)
    connection_id = fields.Str(required=False)


class GetIssueSelfSchema(Schema):
    issue_id = fields.Str(required=False)
    connection_id = fields.Str(required=False)
    exchange_id = fields.Str(required=False)
    service_id = fields.Str(required=False)
    label = fields.Str(required=False)
    author = fields.Str(required=False)
    state = fields.Str(required=False)


@docs(
    tags=["Verifiable Services"],
    summary="Apply to a service that connected agent provides",
    description="""
    "connection_id" - id of a already established connection with some other agent.
    "service" - you can get that by requesting a list of services from a already
    connected agent.
    "payload" - your data.
    """,
)
@request_schema(ApplySchema())
async def apply(request: web.BaseRequest):
    context = request.app["request_context"]
    params = await request.json()
    outbound_handler = request.app["outbound_message_router"]

    connection_id = params["connection_id"]
    payload = params["payload"]

    service_id = params["service"]["service_id"]
    consent_schema = params["service"]["consent_schema"]
    service_schema = params["service"]["service_schema"]
    label = params["service"]["label"]

    try:
        connection: ConnectionRecord = await ConnectionRecord.retrieve_by_id(
            context, connection_id
        )
    except StorageNotFoundError:
        raise web.HTTPNotFound(reason="Connection not found")
    #
    # NOTE(KKrzosa): Send a credential offer for consent to the other agent
    # TODO(KKrzosa): Cache the credential definition
    #

    ledger: BaseLedger = await context.inject(BaseLedger)
    issuer: BaseIssuer = await context.inject(BaseIssuer)

    try:
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
    except (LedgerError, IssuerError, BadLedgerRequestError) as err:
        LOGGER.error(
            "credential offer creation error! %s", err,
        )
        raise web.HTTPError(reason="Ledger error, credential offer creation error")

    (
        credential_exchange_record,
        credential_offer_message,
    ) = await create_consent_credential_offer(
        context=context,
        cred_def_id=credential_definition_id,
        connection_id=connection_id,
        consent_schema=consent_schema,
        auto_issue=True,
        auto_remove=True,
    )

    if connection.is_ready:
        await outbound_handler(credential_offer_message, connection_id=connection_id)

        record = ServiceIssueRecord(
            connection_id=connection_id,
            state=ServiceIssueRecord.ISSUE_WAITING_FOR_RESPONSE,
            author=ServiceIssueRecord.AUTHOR_SELF,
            service_id=service_id,
            label=label,
            consent_schema=consent_schema,
            service_schema=service_schema,
            payload=payload,
            credential_definition_id=credential_exchange_record.credential_definition_id,
        )

        data_dri = await record.save(context)

        request = Application(
            service_id=record.service_id,
            exchange_id=record.exchange_id,
            credential_definition_id=credential_exchange_record.credential_definition_id,
            data_dri=data_dri,
        )
        await outbound_handler(request, connection_id=connection_id)
        return web.json_response(request.serialize())

    raise web.HTTPBadGateway


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

    #
    # NOTE(KKrzosa): Validate the state of the issue and
    #                check if credential is correct
    # TODO(KKrzosa): inform about invalid credential
    #

    if params["decision"] == "reject" or issue.state == REJECTED:
        issue.state = REJECTED
        issue.save()
        confirmer.send_confirmation(REJECTED)
        return web.json_response(issue.serialize())

    holder: BaseHolder = await context.inject(BaseHolder)

    service_namespace = service.consent_schema["oca_schema_namespace"]
    service_dri = service.consent_schema["oca_schema_dri"]
    service_data_url = service.consent_schema["data_url"]

    # NOTE(KKrzosa): Search for a consent credential
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

    #
    # NOTE(KKrzosa): Create a schema and credential def but only if they dont exist
    #                 and based on those issue a credential
    #

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
                        "name": "oca_schema_dri",
                        "mime-type": "application/json",
                        "value": service.service_schema["oca_schema_dri"],
                    },
                    {
                        "name": "data_dri",
                        "mime-type": "application/json",
                        "value": issue.issuer_data_dri_cache,
                    },
                    {
                        "name": "oca_schema_namespace",
                        "mime-type": "application/json",
                        "value": service.service_schema["oca_schema_namespace"],
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
        raise web.HTTPError(reason="Ledger error, credential offer creation error")

    issue.state = ACCEPTED
    await issue.save(context, reason="Accepted service issue, credential offer created")

    await outbound_handler(credential_offer_message, connection_id=issue.connection_id)
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

    IMPORTANT: when issue_id is passed, all other fields are IGNORED!
    issue_id == data_dri

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

    # TODO: Under the hood payload change notification
    if params["issue_id"] != None:
        try:
            query = [
                await ServiceIssueRecord.retrieve_by_id(context, params["issue_id"])
            ]
        except StorageNotFoundError:
            raise web.HTTPNotFound
    else:
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


# @docs(
#     tags=["Verifiable Services"],
#     summary="Get state of a service issue",
#     description="""
#     You can filter issues by:
#         service_id
#         connection_id
#         exchange_id (id of a group of issue messages)

#     This returns a list, you can exclude a filter just by not including it
#     so if you dont want to search by exchange_id make sure to only include:
#         {"connection_id": "123", "service_id": "1234"}
#     """,
# )
@request_schema(ApplyStatusSchema())
async def DEBUGapply_status(request: web.BaseRequest):
    context = request.app["request_context"]
    params = await request.json()

    try:
        query = await ServiceIssueRecord.query(context, tag_filter=params)
    except StorageNotFoundError:
        raise web.HTTPNotFound

    query = [i.serialize() for i in query]

    return web.json_response(query)


async def DEBUGget_credential_data(request: web.BaseRequest):
    context = request.app["request_context"]
    data_dri = request.match_info["data_dri"]

    try:
        query: ServiceIssueRecord = await ServiceIssueRecord.retrieve_by_id(
            context, data_dri
        )
    except StorageNotFoundError:
        raise web.HTTPNotFound

    return web.json_response({"credential_data": query.payload})
