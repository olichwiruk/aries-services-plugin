from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.messaging.responder import BaseResponder, MockResponder
from aries_cloudagent.storage.base import BaseStorage, StorageRecord
from aries_cloudagent.storage.basic import BasicStorage
from asynctest import TestCase as AsyncTestCase, mock as async_mock

import hashlib
from marshmallow import fields
from unittest import mock, TestCase
import json

from ..records import *


class TestSchemaExchangeRecord(AsyncTestCase):
    payload = "{Test Payload}"
    hashid = hashlib.sha256(payload.encode("UTF-8")).hexdigest()
    author = "self"
    state = "pending"
    connection_id = "1234"

    def testInit(self):
        record = SchemaExchangeRecord(
            payload=self.payload,
            author=self.author,
            connection_id=self.connection_id,
            state=self.state,
        )
        assert self.payload == record.payload
        assert self.author == record.author

    async def testSaveAndRetrieve(self):
        context = InjectionContext()
        storage = BasicStorage()
        context.injector.bind_instance(BaseStorage, storage)

        record = SchemaExchangeRecord(
            payload=self.payload,
            author=self.author,
            connection_id=self.connection_id,
            state=self.state,
        )
        record_id = await record.save(context)
        assert record_id == self.hashid
        assert record.payload == self.payload
        assert record.author == self.author
        assert record.state == self.state

        query = await SchemaExchangeRecord.retrieve_by_id(context, self.hashid)
        assert query == record


class TestSchemaExchangeRequestRecord(AsyncTestCase):
    payload = "{Test Payload}"
    state = "pending"
    author_connection_id = "1234"

    def testInit(self):
        record = SchemaExchangeRequestRecord(
            payload=self.payload,
            state=self.state,
            author_connection_id=self.author_connection_id,
        )
        assert self.payload == record.payload
        assert self.author_connection_id == record.author_connection_id

    async def testSaveAndRetrieve(self):
        context = InjectionContext()
        storage = BasicStorage()
        context.injector.bind_instance(BaseStorage, storage)

        record = SchemaExchangeRequestRecord(
            payload=self.payload,
            state=self.state,
            author_connection_id=self.author_connection_id,
        )

        record_id = await record.save(context)
        assert record_id != 0
        assert record.payload == self.payload
        assert record.author_connection_id == self.author_connection_id
        assert record.state == self.state

        query = await SchemaExchangeRequestRecord.retrieve_by_id(context, record_id)
        assert query == record
