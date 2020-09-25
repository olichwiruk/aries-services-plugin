from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.messaging.responder import BaseResponder, MockResponder
from aries_cloudagent.storage.base import BaseStorage, StorageRecord
from aries_cloudagent.storage.basic import BasicStorage
from asynctest import TestCase as AsyncTestCase, mock as async_mock

import hashlib
from marshmallow import fields
from unittest import mock, TestCase
import json

from ..models import SchemaExchangeRecord, SchemaExchangeRecordSchema
from ..handlers import *


class TestSchemaExchangeResponse(AsyncTestCase):
    payload = "{Test Payload}"
    author = "other"
    connection_id = "1234"
    state = "pending"

    content = payload + author + connection_id + state
    request_hash = hashlib.sha256(content.encode("UTF-8")).hexdigest()
    hash_id = hashlib.sha256(payload.encode("UTF-8")).hexdigest()

    async def create_default_context(self):
        context = RequestContext()
        storage = BasicStorage()
        responder = MockResponder()

        context.injector.bind_instance(BaseStorage, storage)

        context.connection_ready = True
        context.connection_record = ConnectionRecord(connection_id=self.connection_id)

        return [context, storage, responder]

    async def testHandlerAccept(self):
        context, storage, responder = await self.create_default_context()

        state = SchemaExchangeRequestRecord.STATE_APPROVED

        record = SchemaExchangeRequestRecord(
            payload=self.payload,
            author=self.author,
            connection_id=self.connection_id,
            state=self.state,
        )

        await record.save(context)
        context.message = Response(
            state=state, payload=self.payload, exchange_id=record.exchange_id,
        )

        handler = ResponseHandler()
        await handler.handle(context, responder)

        assert len(responder.messages) == 0
        assert len(responder.webhooks) == 1
        assert responder.webhooks[0] == (
            "schema_exchange",
            {
                "hash_id": self.hash_id,
                "connection_id": self.connection_id,
                "payload": self.payload,
                "state": state,
            },
        )
        record = await SchemaExchangeRecord.retrieve_by_id(context, self.hash_id)

    async def testHandlerReject(self):
        context, storage, responder = await self.create_default_context()

        state = SchemaExchangeRequestRecord.STATE_DENIED

        record = SchemaExchangeRequestRecord(
            payload=self.payload,
            author=self.author,
            connection_id=self.connection_id,
            state=self.state,
        )

        await record.save(context)
        record_id = record.exchange_id

        context.message = Response(
            state=state, payload=self.payload, exchange_id=record.exchange_id,
        )
        assert context.message.state == state
        assert context.message.payload == self.payload

        handler = ResponseHandler()
        await handler.handle(context, responder)

        record = None
        try:
            record = await SchemaExchangeRecord.retrieve_by_id(context, self.hash_id)
        except:
            pass
        finally:
            assert record == None
        assert len(responder.messages) == 0
        assert len(responder.webhooks) == 1
        assert responder.webhooks[0] == (
            "schema_exchange",
            {
                "hash_id": None,
                "connection_id": self.connection_id,
                "payload": self.payload,
                "state": state,
            },
        )

