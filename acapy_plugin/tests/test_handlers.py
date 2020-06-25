from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.messaging.responder import BaseResponder, MockResponder
from aries_cloudagent.messaging.request_context import RequestContext
from aries_cloudagent.storage.base import BaseStorage, StorageRecord
from aries_cloudagent.storage.basic import BasicStorage
from asynctest import TestCase as AsyncTestCase, mock as async_mock
from ..records import SchemaExchangeRecord, SchemaExchangeRecordSchema
from ..schema_exchange import GetHandler, Get

import hashlib
from marshmallow import fields
from unittest import mock, TestCase
import json


class TestSchemaExchangeGetHandler(AsyncTestCase):
    payload = "{Test Payload}"
    hashid = hashlib.sha256(payload.encode("UTF-8")).hexdigest()
    author = "self"

    async def testGetHandler(self):
        context = InjectionContext()
        ctx = RequestContext(base_context=context)
        storage = BasicStorage()
        responder = MockResponder()
        context.injector.bind_instance(BaseStorage, storage)

        record = SchemaExchangeRecord(payload=self.payload, author=self.author)
        await record.save(context)
        ctx.message = Get(hashid=self.hashid)

        handler = GetHandler()
        await handler.handle(ctx, responder)
        messages = responder.messages
        assert len(messages) == 1
        result, target = messages[0]
        isinstance(result, Get)
        assert result.hashid == record.hashid
