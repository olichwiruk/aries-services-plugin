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
    author = "other"
    connection_id = "1234"
    state = "pending"

    content = payload + author + connection_id + state
    request_hash = hashlib.sha256(content.encode("UTF-8")).hexdigest()
    hashid = hashlib.sha256(payload.encode("UTF-8")).hexdigest()

    async def testHandlerAccept(self):
        context = RequestContext()
        storage = BasicStorage()
        responder = MockResponder()

        context.injector.bind_instance(BaseStorage, storage)
        decision = SchemaExchangeRequestRecord.STATE_ACCEPTED

        context.connection_ready = True
        context.connection_record = ConnectionRecord(connection_id=self.connection_id)

        record = SchemaExchangeRequestRecord(
            payload=self.payload,
            author=self.author,
            connection_id=self.connection_id,
            state=self.state,
        )

        await record.save(context)
        context.message = Response(
            decision=decision,
            payload=self.payload,
            cross_planetary_identification_number=record.cross_planetary_identification_number,
        )

        handler = ResponseHandler()
        await handler.handle(context, responder)

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
        record = await SchemaExchangeRecord.retrieve_by_id(context, self.hashid)

    async def testHandlerReject(self):
        context = RequestContext()
        storage = BasicStorage()
        responder = MockResponder()

        decision = SchemaExchangeRequestRecord.STATE_REJECTED
        context.injector.bind_instance(BaseStorage, storage)

        context.connection_ready = True
        context.connection_record = ConnectionRecord(connection_id=self.connection_id)

        record = SchemaExchangeRequestRecord(
            payload=self.payload,
            author=self.author,
            connection_id=self.connection_id,
            state=self.state,
        )

        await record.save(context)
        record_id = record.cross_planetary_identification_number

        context.message = Response(
            decision=decision,
            payload=self.payload,
            cross_planetary_identification_number=record.cross_planetary_identification_number,
        )
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
                "hashid": SchemaExchangeRequestRecord.STATE_REJECTED,
                "connection_id": self.connection_id,
                "payload": self.payload,
                "state": decision,
            },
        )

