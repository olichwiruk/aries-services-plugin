from aries_cloudagent.config.injection_context import InjectionContext
from ..records import SchemaExchangeRecord, SchemaExchangeRecordSchema
from aries_cloudagent.messaging.responder import BaseResponder, MockResponder
from aries_cloudagent.storage.base import BaseStorage, StorageRecord
from aries_cloudagent.storage.basic import BasicStorage
from asynctest import TestCase as AsyncTestCase, mock as async_mock

import hashlib
from marshmallow import fields
from unittest import mock, TestCase
import json


class TestSchemaExchangeRecord(AsyncTestCase):
    payload = "{Test Payload}"
    hashid = hashlib.sha256(payload.encode("UTF-8")).hexdigest()
    author = "self"

    def testInit(self):
        record = SchemaExchangeRecord(payload=self.payload, author=self.author)
        assert self.hashid == record.hashid

        record = SchemaExchangeRecord(
            payload=self.payload, author=self.author, hashid=self.hashid)
        assert self.hashid == record.hashid

    async def testSaveAndRetrieve(self):
        context = InjectionContext()
        storage = BasicStorage()
        context.injector.bind_instance(BaseStorage, storage)
        record = SchemaExchangeRecord(payload=self.payload, author=self.author)
        record_id = await record.save(context)
        query = await SchemaExchangeRecord.retrieve_by_hashid(context, record.hashid)
        assert query == record

        # query = await SchemaExchangeRecord.query(context, post_filter_positive={"hashid": record.hashid})
        # assert query == self.payload

    # async def test_query(self):
    #     context = InjectionContext(enforce_typing=False)
    #     mock_storage = async_mock.MagicMock(BaseStorage, autospec=True)
    #     context.injector.bind_instance(BaseStorage, mock_storage)
    #     record_id = "record_id"
    #     record_value = {"created_at": time_now(), "updated_at": time_now()}
    #     tag_filter = {"tag": "filter"}
    #     stored = StorageRecord(
    #         BaseRecordImpl.RECORD_TYPE, json.dumps(record_value), {}, record_id
    #     )

    #     mock_storage.search_records.return_value.__aiter__.return_value = [stored]
    #     result = await BaseRecordImpl.query(context, tag_filter)
    #     mock_storage.search_records.assert_called_once_with(
    #         BaseRecordImpl.RECORD_TYPE, tag_filter, None, {"retrieveTags": False}
    #     )
    #     assert result and isinstance(result[0], BaseRecordImpl)
    #     assert result[0]._id == record_id
    #     assert result[0].value == record_value

    # async def test_post_save_exist(self):
    #     context = InjectionContext(enforce_typing=False)
    #     mock_storage = async_mock.MagicMock()
    #     mock_storage.update_record_value = async_mock.CoroutineMock()
    #     mock_storage.update_record_tags = async_mock.CoroutineMock()
    #     context.injector.bind_instance(BaseStorage, mock_storage)
    #     record = BaseRecordImpl()
    #     last_state = "last_state"
    #     record._last_state = last_state
    #     record._id = "id"
    #     with async_mock.patch.object(
    #         record, "post_save", async_mock.CoroutineMock()
    #     ) as post_save:
    #         await record.save(context, reason="reason", webhook=False)
    #         post_save.assert_called_once_with(context, False, last_state, False)
    #     mock_storage.update_record_value.assert_called_once()
    #     mock_storage.update_record_tags.assert_called_once()
