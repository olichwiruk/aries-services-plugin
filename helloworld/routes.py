"""Hello world service"""

import logging

from aiohttp import web
from aiohttp_apispec import docs
from marshmallow import Schema, fields

from ...core.protocol_registry import ProtocolRegistry

LOGGER = logging.getLogger(__name__)


@docs(tags=["Hello world"],
      summary="Simple protocol made just to show that I can do it")
async def hello_world(request: web.BaseRequest):
    """
    Request handler for the simplest possible hello world type of thing

    Args:
        request: aiohttp request object

    """
    LOGGER.info("HELLO WORLD REQUESTED :^)")

    result = {
        "message": "Hello world"
    }
    
    return web.json_response(result)


async def register(app: web.Application):
    """Register routes."""

    app.add_routes([
        web.post("/hello-world", hello_world)
        ])
