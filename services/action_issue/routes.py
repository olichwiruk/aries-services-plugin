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

from ..issue.message_types import Application
from ..discovery.models import ConsentSchema, ServiceSchema, ServiceDiscoveryRecord
from ..issue.models import ServiceIssueRecord

from aries_cloudagent.protocols.actionmenu.v1_0.messages.menu import Menu
from aries_cloudagent.protocols.actionmenu.v1_0.routes import MenuJsonSchema
from aries_cloudagent.protocols.actionmenu.v1_0.messages.menu_request import MenuRequest
from aries_cloudagent.protocols.actionmenu.v1_0.messages.perform import Perform
from aries_cloudagent.protocols.actionmenu.v1_0.models.menu_option import (
    MenuOptionSchema,
)
from aries_cloudagent.protocols.actionmenu.v1_0.util import (
    retrieve_connection_menu,
    save_connection_menu,
)

LOGGER = logging.getLogger(__name__)


class ApplyForMenuSchema(Schema):
    service_id = fields.Str(required=True)


@docs(
    tags=["Verifiable Services"],
    summary="Apply to a service that connected agent provides, you need a service_id that you can get from service discovery request list",
)
@request_schema(ApplyForMenuSchema())
async def send_services_menu(request: web.BaseRequest):
    context = request.app["request_context"]
    connection_id = request.match_info["connection_id"]
    outbound_handler = request.app["outbound_message_router"]
    params = await request.json()

    try:
        connection: ConnectionRecord = await ConnectionRecord.retrieve_by_id(
            context, connection_id
        )
        services: ServiceDiscoveryRecord = await ServiceDiscoveryRecord.retrieve_by_connection_id(
            context, connection_id
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

    record = ServiceIssueRecord(
        connection_id=connection_id,
        state=ServiceIssueRecord.ISSUE_WAITING_FOR_RESPONSE,
        author=ServiceIssueRecord.AUTHOR_SELF,
        service_id=service["service_id"],
        label=service["label"],
    )

    await record.save(context)

    LOGGER.info("Received send-menu request: %s %s", connection_id, params)
    try:
        menu = MenuJsonSchema()
        menu = menu.dump(
            {
                "title": "testMenu",
                "description": "test menu description",
                "options": [{"name": "test option", "title": "test title",}],
            }
        )
        msg = Menu.deserialize(menu)
    except Exception:
        LOGGER.exception("Exception deserializing menu")
        raise

    if connection.is_ready:
        await outbound_handler(msg, connection_id=connection_id)
        return web.json_response({})

    raise web.HTTPForbidden()


# @docs(
#     tags=["Verifiable Services"], summary="Request a service menu",
# )
# async def request_services_menu(request: web.BaseRequest):
#     context = request.app["request_context"]
#     connection_id = request.match_info["connection_id"]
#     outbound_handler = request.app["outbound_message_router"]
#     params = await request.json()

#     try:
#         connection: ConnectionRecord = await ConnectionRecord.retrieve_by_id(
#             context, connection_id
#         )
#     except StorageNotFoundError:
#         raise web.HTTPNotFound

#     record = ServiceIssueRecord(
#         connection_id=connection_id,
#         state=ServiceIssueRecord.ISSUE_WAITING_FOR_RESPONSE,
#         author=ServiceIssueRecord.AUTHOR_SELF,
#         service_id=service["service_id"],
#         label=service["label"],
#     )

#     await record.save(context)

#     LOGGER.info("Received send-menu request: %s %s", connection_id, params)
#     try:
#         menu = MenuJsonSchema()
#         menu = menu.dump(
#             {
#                 "title": "testMenu",
#                 "description": "test menu description",
#                 "options": [{"name": "test option", "title": "test title",}],
#             }
#         )
#         msg = Menu.deserialize(menu)
#     except Exception:
#         LOGGER.exception("Exception deserializing menu")
#         raise

#     if connection.is_ready:
#         await outbound_handler(msg, connection_id=connection_id)
#         return web.json_response({})

#     raise web.HTTPForbidden()
