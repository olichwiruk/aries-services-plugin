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
from ..consents.models.given_consent import ConsentGivenRecord
from .credentials import *
from ..discovery.message_types import DiscoveryServiceSchema
from aries_cloudagent.pdstorage_thcf.api import *
from aries_cloudagent.protocols.issue_credential.v1_1.messages.credential_request import (
    CredentialRequest,
)
from aries_cloudagent.protocols.issue_credential.v1_1.utils import (
    create_credential,
    retrieve_connection,
)

from ..util import retrieve_service, retrieve_service_issue

LOGGER = logging.getLogger(__name__)


class ApplySchema(Schema):
    connection_id = fields.Str(required=True)
    user_data = fields.Str(required=True)
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
    service_user_data = params["user_data"]
    service_id = params["service"]["service_id"]
    consent_schema = params["service"]["consent_schema"]
    service_schema = params["service"]["service_schema"]
    label = params["service"]["label"]

    connection = await retrieve_connection(context, connection_id)
    issuer: BaseIssuer = await context.inject(BaseIssuer)

    """

    Issue consent credential for service provider

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

    service_user_data_dri = await save_string(context, service_user_data)

    record = ServiceIssueRecord(
        connection_id=connection_id,
        state=ServiceIssueRecord.ISSUE_WAITING_FOR_RESPONSE,
        author=ServiceIssueRecord.AUTHOR_SELF,
        label=label,
        consent_schema=consent_schema,
        service_id=service_id,
        service_schema=service_schema,
        service_user_data_dri=service_user_data_dri,
        service_consent_match_id=service_consent_match_id,
    )

    await record.save(context)

    """ 
    NOTE: service_user_data_dri - is here so that in the future it would be easier
          to not send the service_user_data, because from what I understand we only
          want to send that to the other party under certain conditions

          dri is used only to make sure DRI's are the same 
          when I store the data in other's agent PDS
    """

    request = Application(
        service_id=record.service_id,
        exchange_id=record.exchange_id,
        service_user_data=service_user_data,
        service_user_data_dri=service_user_data_dri,
        service_consent_match_id=service_consent_match_id,
        consent_credential=credential,
    )
    await outbound_handler(request, connection_id=connection_id)

    """

    record the given credential

    """

    consent_given_record = ConsentGivenRecord(
        consent_user_data_dri=consent_schema["data_dri"],
        connection_id=connection_id,
        credential=credential,
        service_consent_match_id=service_consent_match_id,
    )

    await consent_given_record.save(context)

    return web.json_response(request.serialize())


async def send_confirmation(outbound_handler, connection_id, exchange_id, state):
    confirmation = Confirmation(exchange_id=exchange_id, state=state)
    await outbound_handler(confirmation, connection_id=connection_id)


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
    exchange_id = issue.exchange_id
    connection_id = issue.connection_id

    service: ServiceRecord = await retrieve_service(context, issue.service_id)
    connection: ConnectionRecord = await retrieve_connection(context, connection_id)

    """

    User can decide to reject the application, this is a check for that

    """

    if (
        params["decision"] == "reject"
        or issue.state == ServiceIssueRecord.ISSUE_REJECTED
    ):
        issue.state = ServiceIssueRecord.ISSUE_REJECTED
        await issue.save(context, reason="Issue reject saved")
        await send_confirmation(
            outbound_handler, connection_id, exchange_id, issue.state
        )
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
                "data_dri": issue.service_user_data_dri,
                "service_consent_match_id": issue.service_consent_match_id,
            }
        },
        connection,
        exception=web.HTTPError,
    )

    issue.state = ServiceIssueRecord.ISSUE_ACCEPTED
    await issue.save(context, reason="Accepted service issue, credential offer created")

    resp = ApplicationResponse(credential=credential, exchange_id=exchange_id)
    await outbound_handler(resp, connection_id=connection_id)
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

        """
        Serialize additional fields which are not serializable
        by default (information that is in PDS)
        """

        service_user_data = await load_string(context, i.service_user_data_dri)

        record.update(
            {
                "issue_id": i._id,
                "label": i.label,
                "service_user_data": service_user_data,
                "service_schema": json.dumps(i.service_schema),
                "consent_schema": json.dumps(i.consent_schema),
            }
        )
        result.append(record)

    return web.json_response(result)


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
