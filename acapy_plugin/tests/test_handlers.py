from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.messaging.responder import BaseResponder, MockResponder
from aries_cloudagent.storage.base import BaseStorage, StorageRecord
from aries_cloudagent.storage.basic import BasicStorage
from asynctest import TestCase as AsyncTestCase, mock as async_mock

import hashlib
from marshmallow import fields
from unittest import mock, TestCase
import json

from ..records import SchemaExchangeRecord, SchemaExchangeRecordSchema
from ..schema_exchange import *


class TestSchemaExchangeResponse(AsyncTestCase):
    payload = "{Test Payload}"
    hashid = hashlib.sha256(payload.encode("UTF-8")).hexdigest()
    author = "other"
    connection_id = "1234"

    async def testHandlerAccept(self):
        decision = SchemaExchangeRecord.STATE_ACCEPTED
        context = RequestContext()
        context.connection_ready = True
        storage = BasicStorage()
        responder = MockResponder()
        context.injector.bind_instance(BaseStorage, storage)
        context.connection_record = ConnectionRecord(connection_id=self.connection_id)
        context.message = Response(decision=decision, payload=self.payload)
        assert context.message.decision == decision
        assert context.message.payload == self.payload

        handler = ResponseHandler()
        await handler.handle(context, responder)

        record = await SchemaExchangeRecord.retrieve_by_id(context, self.hashid)
        record.connection_id == self.connection_id
        record.author = self.author
        record.payload = self.payload
        assert len(responder.messages) == 0
        assert len(responder.webhooks) == 1
        assert responder.webhooks[0] == (
            "schema_exchange",
            {
                "hashid": self.hashid,
                "connection_id": self.connection_id,
                "payload": self.payload,
                "state": decision,
            },
        )

    async def testHandlerReject(self):
        decision = SchemaExchangeRecord.STATE_REJECTED
        context = RequestContext()
        context.connection_ready = True
        storage = BasicStorage()
        responder = MockResponder()
        context.injector.bind_instance(BaseStorage, storage)
        context.connection_record = ConnectionRecord(connection_id=self.connection_id)
        context.message = Response(decision=decision, payload=self.payload)
        assert context.message.decision == decision
        assert context.message.payload == self.payload

        handler = ResponseHandler()
        await handler.handle(context, responder)

        record = None
        try:
            record = await SchemaExchangeRecord.retrieve_by_id(context, self.hashid)
        except:
            pass
        finally:
            assert record == None
        assert len(responder.messages) == 0
        assert len(responder.webhooks) == 1
        assert responder.webhooks[0] == (
            "schema_exchange",
            {
                "hashid": None,
                "connection_id": self.connection_id,
                "payload": self.payload,
                "state": decision,
            },
        )

