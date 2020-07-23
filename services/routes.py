from aries_cloudagent.connections.models.connection_record import ConnectionRecord
from aries_cloudagent.messaging.valid import UUIDFour
from aries_cloudagent.storage.error import StorageNotFoundError, StorageDuplicateError
from aries_cloudagent.storage.base import BaseStorage

from aiohttp import web
from aiohttp_apispec import docs, request_schema

from marshmallow import fields, Schema
import logging
import hashlib
from typing import Sequence

# Internal
from .discovery.records import (
    ServiceRecord,
    ConsentSchema,
    ServiceSchema,
    ServiceDiscoveryRecord,
)
from .discovery.message_types import Discovery
from .issue.message_types import Application


class AddServiceSchema(Schema):
    label = fields.Str(required=True)
    service_schema = fields.Nested(ServiceSchema())
    consent_schema = fields.Nested(ConsentSchema())


@request_schema(AddServiceSchema())
@docs(tags=["verifiable-services"], summary="Add a verifiable service")
async def add_service(request: web.BaseRequest):
    context = request.app["request_context"]
    params = await request.json()

    serviceRecord = ServiceRecord(
        label=params["label"],
        service_schema=params["service_schema"],
        consent_schema=params["consent_schema"],
    )

    try:
        hash_id = await serviceRecord.save(context)
    except StorageDuplicateError:
        pass

    return web.json_response(serviceRecord.serialize())


@docs(
    tags=["verifiable-services"],
    summary="Request a list of services from another agent",
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
        return web.json_response(request.serialize())

    return web.json_response("failed")


@docs(
    tags=["verifiable-services"],
    summary="Get the saved list of services from another agent",
)
async def get_service_list(request: web.BaseRequest):
    context = request.app["request_context"]
    connection_id = request.match_info["connection_id"]

    try:
        query: ServiceDiscoveryRecord = await ServiceDiscoveryRecord().retrieve_by_connection_id(
            context, connection_id
        )
    except StorageNotFoundError:
        return web.json_response("Services for this connection id not found")

    return web.json_response(query.serialize())


async def apply(request: web.BaseRequest):
    context = request.app["request_context"]
    params = await request.json()
    outbound_handler = request.app["outbound_message_router"]

    try:
        connection: ConnectionRecord = await ConnectionRecord.retrieve_by_id(
            context, connection_id
        )
    except StorageNotFoundError:
        raise web.HTTPNotFound

    # TODO:
    if connection.is_ready:
        request = Application()
        await outbound_handler(request, connection_id=connection_id)
        return web.json_response(request.serialize())

    return web.json_response("connection not ready")


async def register(app: web.Application):
    app.add_routes(
        [
            web.post("/verifiable-services/add-services", add_service),
            web.post("/verifiable-services/apply", apply),
            web.get(
                "/verifiable-services/request-list/{connection_id}",
                request_services_list,
                allow_head=False,
            ),
            web.get(
                "/verifiable-services/get-list/{connection_id}",
                get_service_list,
                allow_head=False,
            ),
        ]
    )
