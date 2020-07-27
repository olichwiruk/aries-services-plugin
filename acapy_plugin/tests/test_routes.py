from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.connections.models.connection_record import ConnectionRecord
from aries_cloudagent.storage.error import StorageNotFoundError
from aries_cloudagent.holder.base import BaseHolder
from aries_cloudagent.messaging.request_context import RequestContext

from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from aiohttp import web as aio_web
import hashlib

from ..handlers import Request


class TestRequestRoutes(AsyncTestCase):
    payload = "{Test Payload}"
    hash_id = hashlib.sha256(payload.encode("UTF-8")).hexdigest()
    author = "self"
    connection_id = "1234"
    state = "pending"

    async def testSend(self):
        context = RequestContext(base_context=InjectionContext())
        requestMock = async_mock.MagicMock()
        requestMock.app = {
            "request_context": context,
            "outbound_message_router": async_mock.CoroutineMock(),
        }
        params = {"connection_id": "1234", "payload": "test, test"}
        hash_id = hashlib.sha256(params["payload"].encode("UTF-8")).hexdigest()
        requestMock.json = async_mock.CoroutineMock(return_value=params)
        ## TODO:

