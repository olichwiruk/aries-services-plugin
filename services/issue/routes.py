from aries_cloudagent.connections.models.connection_record import ConnectionRecord
from aries_cloudagent.messaging.valid import UUIDFour
from aries_cloudagent.storage.error import StorageNotFoundError, StorageDuplicateError

from aries_cloudagent.ledger.error import LedgerError
from aries_cloudagent.indy.error import IndyError
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
from aries_cloudagent.pdstorage_thcf.api import *
from aries_cloudagent.protocols.issue_credential.v1_1.messages.credential_request import (
    CredentialRequest,
)
from aries_cloudagent.protocols.issue_credential.v1_1.utils import create_credential

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


class ProcessApplicationSchema(Schema):
    issue_id = fields.Str(required=True)
    decision = fields.Str(required=True)


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
    outbound_handler = request.app["outbound_message_router"]

    params = await request.json()
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

    issuer: BaseIssuer = await context.inject(BaseIssuer)

    if connection.is_ready:

        """
        Issue consent credential for other party (offer credential -> automatic consent issue)

        This should be rethought I think, perhaps present self certifying credential?
        This either way probably should be a presentation instead of issue
        or maybe a credential after some thought?
        that way the other person can save it

        """

        service_consent_match_id = str(uuid.uuid4())
        credential = await create_credential(
            context,
            {
                "credential_values": {
                    "oca_schema_dri": consent_schema["oca_schema_dri"],
                    "oca_schema_namespace": consent_schema["oca_schema_namespace"],
                    "data_dri": consent_schema["data_dri"],
                    "service_consent_match_id": service_consent_match_id,
                }
            },
            connection,
            exception=web.HTTPError,
        )

        # PROBLEM: From front end perspective we need a panel which has all consents given
        # SOLUTION1: Query for all service applications and retrieve the consent
        # SOLUTION2: Save all consents through higher level api which will make
        #            creating consents more clear, also I can now pump all the information
        #            into one place

        payload_dri = await save_string(context, payload)
        record = ServiceIssueRecord(
            connection_id=connection_id,
            state=ServiceIssueRecord.ISSUE_WAITING_FOR_RESPONSE,
            author=ServiceIssueRecord.AUTHOR_SELF,
            service_id=service_id,
            label=label,
            consent_schema=consent_schema,
            service_schema=service_schema,
            payload_dri=payload_dri,
            service_consent_match_id=service_consent_match_id,
        )

        data_dri = await record.save(context)

        request = Application(
            service_id=record.service_id,
            exchange_id=record.exchange_id,
            data_dri=data_dri,
            service_consent_match_id=service_consent_match_id,
            consent_credential=credential,
        )
        await outbound_handler(request, connection_id=connection_id)
        return web.json_response(request.serialize())

    raise web.HTTPBadGateway(reason="Agent to agent connection is not ready")


# TODO: Connection record, connection ready
class StatusConfirmer:
    def __init__(self, outbound_handler, connection_id, exchange_id):
        self.outbound_handler = outbound_handler
        self.connection_id = connection_id
        self.exchange_id = exchange_id

    async def send_confirmation(self, state):
        confirmation = Confirmation(exchange_id=self.exchange_id, state=state)
        await self.outbound_handler(confirmation, connection_id=self.connection_id)


from ..util import retrieve_service, retrieve_service_issue


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
    issue_id = params["issue_id"]

    issue: ServiceIssueRecord = await retrieve_service_issue(context, issue_id)
    service: ServiceRecord = await retrieve_service(context, issue.service_id)
    connection_id = issue.connection_id
    exchange_id = issue.exchange_id

    confirmer = StatusConfirmer(outbound_handler, connection_id, exchange_id)

    """

    User can decide to reject the application, this is a check for that

    """

    if (
        params["decision"] == "reject"
        or issue.state == ServiceIssueRecord.ISSUE_REJECTED
    ):
        issue.state = ServiceIssueRecord.ISSUE_REJECTED
        await issue.save(context, reason="Issue reject saved")
        await confirmer.send_confirmation(issue.state)
        return web.json_response(issue.serialize())

    """

    Create a service credential with values from the applicant

    """

    credential = await create_credential(
        context,
        {
            "credential_values": {
                "oca_schema_dri": service.service_schema["oca_schema_dri"],
                "oca_schema_namespace": service.service_schema["oca_schema_namespace"],
                "data_dri": issue.payload_dri,
                "service_consent_match_id": issue.service_consent_match_id,
            }
        },
        connection_id,
        exception=web.HTTPError,
    )

    issue.state = ServiceIssueRecord.ISSUE_ACCEPTED
    await issue.save(context, reason="Accepted service issue, credential offer created")
    await confirmer.send_confirmation(issue.state)

    await outbound_handler(credential_offer_message, connection_id=connection_id)
    return web.json_response(
        {
            "issue_id": issue._id,
            "connection_id": connection_id,
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
    # ERROR:
    if "issue_id" in params and params["issue_id"] != None:
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

        # NOTE(Krzosa): request additional information from the agent
        # that we had this interaction with
        if i.payload_dri == None:
            request = GetIssue(exchange_id=i.exchange_id)
            await outbound_handler(request, connection_id=i.connection_id)

        # NOTE(Krzosa): serialize additional fields which are not serializable
        # by default
        payload = await load_string(context, i.payload_dri)

        record.update(
            {
                "issue_id": i._id,
                "label": i.label,
                "payload": payload,
                "service_schema": json.dumps(i.service_schema),
                "consent_schema": json.dumps(i.consent_schema),
            }
        )
        result.append(record)

    return web.json_response(result)


@docs(
    tags=["Verifiable Services"],
    summary="Get state of a service issue",
    description="""
    You can filter issues by:
        service_id
        connection_id
        exchange_id (id of a group of issue messages)

    This returns a list, you can exclude a filter just by not including it
    so if you dont want to search by exchange_id make sure to only include:
        {"connection_id": "123", "service_id": "1234"}
    """,
)
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
