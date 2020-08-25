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

from ..handlers import *

from ...discovery.message_types import *


class TestDiscovery(AsyncTestCase):
    connection_id = "1234"

    consent_schema = {
        "oca_schema_dri": "1234",
        "oca_schema_namespace": "test",
        "data_url": "http://test.com/test",
    }

    service_schema = {
        "oca_schema_dri": "1234",
        "oca_schema_namespace": "test",
    }

    label = "abcd"

    service = {
        "consent_schema": consent_schema,
        "service_schema": service_schema,
        "label": label,
        "service_id": "1234",
    }

    async def test_discovery_response_handler(self):
        context = RequestContext()
        storage = BasicStorage()
        responder = MockResponder()

        context.injector.bind_instance(BaseStorage, storage)

        context.connection_ready = True
        context.connection_record = ConnectionRecord(connection_id=self.connection_id)

        context.message = DiscoveryResponse(services=[self.service])

        handler = DiscoveryResponseHandler()
        await handler.handle(context, responder)

    async def test_discovery_handler(self):
        context = RequestContext()
        storage = BasicStorage()
        responder = MockResponder()

        context.injector.bind_instance(BaseStorage, storage)

        record = ServiceRecord(
            consent_schema=self.consent_schema,
            service_schema=self.service_schema,
            label=self.label,
        )
        service_id = await record.save(context=context)

        context.message = Discovery()

        handler = DiscoveryHandler()
        await handler.handle(context, responder)
        assert len(responder.messages) == 1
        assert isinstance(responder.messages[0][0], DiscoveryResponse)
        assert service_id == responder.messages[0][0].services[0]["service_id"]
