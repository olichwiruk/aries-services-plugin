from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.messaging.responder import BaseResponder, MockResponder
from aries_cloudagent.connections.models.connection_record import ConnectionRecord
from aries_cloudagent.messaging.request_context import RequestContext
from aries_cloudagent.storage.base import BaseStorage, StorageRecord
from aries_cloudagent.storage.basic import BasicStorage
from asynctest import TestCase as AsyncTestCase, mock as async_mock
from ..records import SchemaExchangeRecord, SchemaExchangeRecordSchema
from ..schema_exchange import *


import hashlib
from marshmallow import fields
from unittest import mock, TestCase
import json
import pytest


class TestSchemaExchangeGetHandler(AsyncTestCase):
    payload = "{Test Payload}"
    hashid = hashlib.sha256(payload.encode("UTF-8")).hexdigest()
    author = "self"
    connection_id = "1234"
    state = "pending"

    async def testGetHandler(self):
        context = InjectionContext()
        ctx = RequestContext(base_context=context)
        storage = BasicStorage()
        responder = MockResponder()
        context.injector.bind_instance(BaseStorage, storage)

        record = SchemaExchangeRecord(
            payload=self.payload,
            author=self.author,
            state=self.state,
            connection_id=self.connection_id,
        )
        await record.save(context)
        ctx.message = Get(hashid=self.hashid)

        handler = GetHandler()
        await handler.handle(ctx, responder)

        messages = responder.messages
        assert len(messages) == 1
        result, target = messages[0]
        isinstance(result, Get)
        assert result.payload["payload"] == record.payload


class TestSchemaExchangeSendResponseHandler(AsyncTestCase):
    payload = '{"Test": Payload}'
    hashid = hashlib.sha256(payload.encode("UTF-8")).hexdigest()
    author = "self"

    @pytest.mark.asyncio
    async def testHandler(self):
        ctx = RequestContext()
        ctx.connection_record = ConnectionRecord(connection_id="1234")
        ctx.connection_ready = True
        storage = BasicStorage()
        responder = MockResponder()
        ctx.injector.bind_instance(BaseStorage, storage)
        ctx.message = SchemaExchange(payload=self.payload, hashid="hashid")

        handler = SchemaExchangeHandler()
        await handler.handle(ctx, responder)
        record = await SchemaExchangeRecord.retrieve_by_id(ctx, self.hashid)
        assert record.payload == self.payload
        assert ctx.connection_record.connection_id == record.connection_id

