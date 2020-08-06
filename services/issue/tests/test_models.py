from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.messaging.responder import BaseResponder, MockResponder
from aries_cloudagent.storage.base import BaseStorage, StorageRecord
from aries_cloudagent.storage.basic import BasicStorage
from asynctest import TestCase as AsyncTestCase, mock as async_mock

import hashlib
from marshmallow import fields
from unittest import mock, TestCase
import datetime
import json

from ..models import *


class TestServiceRecord(AsyncTestCase):
    consent_schema = {
        "oca_schema_dri": "1234",
        "oca_schema_namespace": "test",
        "data_url": "http://test.com/test",
    }
    service_schema = {
        "oca_schema_dri": "1234",
        "oca_schema_namespace": "test",
    }
    label = "test_label"
    payload = "test_payload"
    connection_id = "1234"
    exchange_id = "123456"
    service_id = "12345"

    state = ServiceIssueRecord.ISSUE_PENDING
    author = ServiceIssueRecord.AUTHOR_SELF

    def assert_self_record(self, record):
        assert self.connection_id == record.connection_id
        assert self.exchange_id == record.exchange_id
        assert self.author == record.author
        assert self.state == record.state
        assert self.consent_schema == record.consent_schema
        assert self.service_schema == record.service_schema
        assert self.service_id == record.service_id
        assert self.payload == record.payload

    def create_record(self):
        record = ServiceIssueRecord(
            state=self.state,
            author=self.author,
            connection_id=self.connection_id,
            exchange_id=self.exchange_id,
            label=self.label,
            payload=self.payload,
            consent_schema=self.consent_schema,
            service_schema=self.service_schema,
            service_id=self.service_id,
        )

        return record

    def create_default_context(self):
        context = InjectionContext()
        storage = BasicStorage()
        context.injector.bind_instance(BaseStorage, storage)

        return [context, storage]

    def test_init(self):
        record = self.create_record()
        self.assert_self_record(record)

    async def test_save_retrieve(self):
        context, storage = self.create_default_context()

        record = self.create_record()
        record_id = await record.save(context)

        record = await ServiceIssueRecord.retrieve_by_id(context, record_id=record_id)
        self.assert_self_record(record)

    async def test_save_and_query(self):
        context, storage = self.create_default_context()
        record = self.create_record()
        record_id = await record.save(context)

        query = await ServiceIssueRecord.query(context)
        assert len(query) == 1
        self.assert_self_record(query[0])

