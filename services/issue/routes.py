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

from .message_types import Application
from ..discovery.models import ConsentSchema, ServiceSchema, ServiceDiscoveryRecord
from .models import ServiceIssueRecord


class ApplySchema(Schema):
    service_id = fields.Str(required=True)
    connection_id = fields.Str(required=True)
    payload = fields.Str(required=True)


class ApplyStatusSchema(Schema):
    service_id = fields.Str(required=False)
    connection_id = fields.Str(required=False)
    exchange_id = fields.Str(required=False)


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
        # query for a service with exact service_id
        service = None
        for query in services.services:
            if query["service_id"] == params["service_id"]:
                service = query
                break
        if service == None:
            raise StorageNotFoundError
    except StorageNotFoundError:
        raise web.HTTPNotFound

    if connection.is_ready:
        record = ServiceIssueRecord(
            connection_id=params["connection_id"],
            state=ServiceIssueRecord.ISSUE_WAITING_FOR_RESPONSE,
            author=ServiceIssueRecord.AUTHOR_SELF,
            service_id=service["service_id"],
            label=service["label"],
            consent_schema=service["consent_schema"],
            service_schema=service["service_schema"],
            payload=params["payload"],
        )

        await record.save(context)

        request = Application(
            service_id=record.service_id, exchange_id=record.exchange_id,
        )
        await outbound_handler(request, connection_id=params["connection_id"])
        return web.json_response(request.serialize())

    raise web.HTTPBadGateway


@docs(
    tags=["Verifiable Services"],
    summary="Apply to a service that connected agent provides, you need a service_id that you can get from service discovery request list",
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


@docs(
    tags=["Verifiable Services"], summary="Get consent schema, payload, service schema",
)
@request_schema(ApplyStatusSchema())
async def get_issue(request: web.BaseRequest):
    context = request.app["request_context"]
    params = await request.json()

    try:
        query = await ServiceIssueRecord.query(context, tag_filter=params)
    except StorageNotFoundError:
        raise web.HTTPNotFound

    result = []
    for i in query:
        record = {
            "label": i.label,
            "payload": i.payload,
            "service_schema": i.service_schema,
            "consent_schema": i.consent_schema,
        }
        result.append(record)

    return web.json_response(result)
