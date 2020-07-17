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

from ..records import *


class TestServiceRecord(AsyncTestCase):
    payload = '{"stuff": "yes"}'
    consentSchema = {
        "did": "1234",
        "name": "THE Authority",
        "version": "1.0",
        "description": "asdasdadasdasda",
        "expiration": datetime.datetime.now().isoformat(),
        "limitation": datetime.datetime.now().isoformat(),
        "dictatedBy": "THE Authority",
        "validityTTL": 1234,
    }

    def testInit(self):
        record = ServiceRecord(payload=self.payload, consent_schema=self.consentSchema)
        assert self.payload == record.payload
        assert self.consentSchema == record.consent_schema

    async def testSaveAndRetrieve(self):
        context = InjectionContext()
        storage = BasicStorage()
        context.injector.bind_instance(BaseStorage, storage)

        record = ServiceRecord(payload=self.payload, consent_schema=self.consentSchema)
        record_id = await record.save(context)

        await record.retrieve_by_id(context, record_id=record_id)
        assert record.payload == self.payload
        assert record.consent_schema == self.consentSchema
