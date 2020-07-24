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
    consentSchema = {
        "oca_schema_dri": "1234",
        "oca_schema_namespace": "test",
        "data_url": "http://test.com/test",
    }
    service_schema = {
        "oca_schema_dri": "1234",
        "oca_schema_namespace": "test",
    }
    label = "service"

    def create_default_context(self):
        context = InjectionContext()
        storage = BasicStorage()
        context.injector.bind_instance(BaseStorage, storage)

        return [context, storage]

    def create_record(self):
        record = ServiceRecord(
            label=self.label,
            service_schema=self.service_schema,
            consent_schema=self.consentSchema,
        )

        return record

    def assert_record(self, record):
        assert self.service_schema == record.service_schema
        assert self.consentSchema == record.consent_schema
        assert self.label == record.label

    def test_init(self):
        record = self.create_record()
        self.assert_record(record)

    async def test_save_retrieve(self):
        context, storage = self.create_default_context()

        record = self.create_record()
        record_id = await record.save(context)

        record = await ServiceRecord.retrieve_by_id(context, record_id=record_id)
        self.assert_record(record)

    async def test_save_query(self):
        context = InjectionContext()
        storage = BasicStorage()
        context.injector.bind_instance(BaseStorage, storage)

        record = self.create_record()
        record_id = await record.save(context)

        query = await ServiceRecord.query(context)

        assert len(query) == 1
        self.assert_record(query[0])

