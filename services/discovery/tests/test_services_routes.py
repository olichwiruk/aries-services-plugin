from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from aries_cloudagent.storage.error import StorageNotFoundError

from .. import routes as test_module


# class TestServicesRoutes(AsyncTestCase):
#     async def test_add_service(self):
#         mock_request = async_mock.CoroutineMock()

#         mock_request.app = {
#             "request_context": "context",
#         }

#         with async_mock.patch.object(
#             test_module, "ServiceRecord", autospec=True
#         ) as mock_service_record, async_mock.patch.object(
#             test_module.web, "json_response"
#         ) as mock_response:

#             mock_service_record.save = async_mock.CoroutineMock()
#             res = await test_module.add(mock_request)
