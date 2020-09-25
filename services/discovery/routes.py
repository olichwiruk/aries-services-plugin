from aries_cloudagent.connections.models.connection_record import ConnectionRecord
from aries_cloudagent.messaging.valid import UUIDFour
from aries_cloudagent.storage.error import StorageNotFoundError, StorageDuplicateError
from aries_cloudagent.storage.base import BaseStorage

from aiohttp import web
from aiohttp import ClientSession
from aiohttp_apispec import docs, request_schema

from marshmallow import fields, Schema
import logging
import hashlib
import time
from typing import Sequence

# Internal
from ..models import *
from .message_types import *
from .handlers import *

# debug

# from aries_cloudagent.wallet.base import BaseWallet
# from aries_cloudagent.wallet.http import HttpWallet
# from aries_cloudagent.wallet.basic import BasicWallet

# DATA_VAULT = "https://data-vault.argo.colossi.network/api/v1/files/"
# CONSENT_EXAMPLE = {
#     "expiration": "3600",
#     "limitation": "3600",
#     "dictatedBy": "somebody",
#     "validityTTL": "3600",
# }


class ConsentContentSchema(Schema):
    expiration = fields.Str(required=True)
    limitation = fields.Str(required=True)
    dictatedBy = fields.Str(required=True)
    validityTTL = fields.Str(required=True)


class AddServiceSchema(Schema):
    label = fields.Str(required=True)
    service_schema = fields.Nested(ServiceSchema())
    consent_schema = fields.Nested(ConsentSchema())


@request_schema(AddServiceSchema())
@docs(tags=["Verifiable Services"], summary="Add a verifiable service")
async def add_service(request: web.BaseRequest):
    context = request.app["request_context"]
    params = await request.json()

    # context.settings.set_value("wallet.type", "http")
    # wallet = HttpWallet()

    # context.injector.bind_instance(BaseWallet, wallet)
    # wallet: BaseWallet = await context.inject(BaseWallet)
    # print(context.settings)

    # wallet.open()

    service_record = ServiceRecord(
        label=params["label"],
        service_schema=params["service_schema"],
        consent_schema=params["consent_schema"],
    )

    # Search for the consent in DataVault and make sure that it exists
    # async with ClientSession() as session:
    #     async with session.get(
    #         DATA_VAULT + params["consent_schema"]["data_dri"]
    #     ) as response:
    #         text: str = await response.text()
    #         if response.status != 200 or text == None:
    #             raise web.HTTPNotFound(reason="Consent not found")

    #         text = json.loads(text)
    #         print(text)
    #         if (
    #             "expiration" not in text
    #             or "limitation" not in text
    #             or "validityTTL" not in text
    #         ):
    #             raise web.HTTPNotFound(reason="Consent, unfamiliar format")

    try:
        hash_id = await service_record.save(context)
    except StorageDuplicateError:
        service_record = ServiceRecord().retrieve_by_id(context)

    return web.json_response(service_record.serialize())


@docs(
    tags=["Service Discovery"],
    summary="Request a list of services from another agent",
    description="Reading the list requires webhook handling",
)
async def request_services_list(request: web.BaseRequest):
    context = request.app["request_context"]
    connection_id = request.match_info["connection_id"]
    outbound_handler = request.app["outbound_message_router"]

    try:
        connection: ConnectionRecord = await ConnectionRecord.retrieve_by_id(
            context, connection_id
        )
    except StorageNotFoundError:
        raise web.HTTPNotFound

    if connection.is_ready:
        request = Discovery()
        await outbound_handler(request, connection_id=connection_id)
        return web.json_response("SUCCESS: request sent, expect a webhook notification")

    raise web.HTTPNotFound


@docs(
    tags=["Service Discovery"], summary="Get a list of all services I registered",
)
async def self_service_list(request: web.BaseRequest):
    context = request.app["request_context"]

    try:
        query = await ServiceRecord().query(context)
    except StorageNotFoundError:
        raise web.HTTPNotFound

    result = []
    for service in query:
        service_json = service.serialize()
        service_json.update({"service_id": service._id})
        result.append(service_json)

    return web.json_response(result)


@docs(
    tags=["Service Discovery"], summary="DEBU*GGGG",
)
async def DEBUGrequest_services_list(request: web.BaseRequest):
    context = request.app["request_context"]
    connection_id = request.match_info["connection_id"]
    outbound_handler = request.app["outbound_message_router"]
    print("DEBUGrequest_services_list")

    try:
        connection: ConnectionRecord = await ConnectionRecord.retrieve_by_id(
            context, connection_id
        )
    except StorageNotFoundError:
        raise web.HTTPNotFound

    if connection.is_ready:
        # First we request service list from second agent
        # It has to go through a different route
        request = DEBUGDiscovery()
        await outbound_handler(request, connection_id=connection_id)

        # So here sleep is used to query records in a loop
        # To finally get the records
        max_retries = 8
        for i in range(max_retries):
            try:
                query: DEBUGServiceDiscoveryRecord = await DEBUGServiceDiscoveryRecord().retrieve_by_connection_id(
                    context, connection_id
                )
                return web.json_response(query.serialize())
            except StorageNotFoundError:
                if i >= max_retries:
                    raise web.HTTPRequestTimeout
            time.sleep(1)

    raise web.HTTPNotFound


# {
#     "proof_request": {
#         "name": "Proof request",
#         "version": "1.0",
#         "nonce": "1234567890",
#         "requested_attributes": {
#             "oca_schema_dri": {
#                 "restrictions": [
#                     {"cred_def_id": "67NyPikkNX2VZ1kPZtycBB:3:CL:1096:consent_schema"}
#                 ],
#                 "name": "oca_schema_dri",
#             },
#             "data_dri": {
#                 "restrictions": [
#                     {"cred_def_id": "67NyPikkNX2VZ1kPZtycBB:3:CL:1096:consent_schema"}
#                 ],
#                 "name": "data_dri",
#             },
#             "oca_schema_namespace": {
#                 "restrictions": [
#                     {"cred_def_id": "67NyPikkNX2VZ1kPZtycBB:3:CL:1096:consent_schema"}
#                 ],
#                 "name": "oca_schema_namespace",
#             },
#         },
#     },
#     "connection_id": "f0653185-3a15-4e9a-95b0-7b0100727a43",
# }

