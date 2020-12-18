from aries_cloudagent.messaging.models.base_record import BaseRecord, BaseRecordSchema
from marshmallow import fields

from ...models import OcaSchema
from aries_cloudagent.pdstorage_thcf.api import *
from aries_cloudagent.pdstorage_thcf.error import *
import json

from aries_cloudagent.storage.error import *
from aiohttp import web


class DefinedConsentRecord(BaseRecord):
    RECORD_ID_NAME = "record_id"
    RECORD_TYPE = "defined_consent"

    class Meta:
        schema_class = "DefinedConsentRecordSchema"

    def __init__(
        self,
        *,
        label: str = None,
        oca_schema: OcaSchema = None,
        payload_dri: str = None,
        state: str = None,
        record_id: str = None,
        **keyword_args,
    ):
        super().__init__(record_id, state, **keyword_args)
        self.label = label
        self.oca_schema = oca_schema
        self.payload_dri = payload_dri

    @property
    def record_value(self) -> dict:
        """Accessor to for the JSON record value properties"""
        return {
            prop: getattr(self, prop) for prop in ("label", "oca_schema", "payload_dri")
        }

    @property
    def record_tags(self) -> dict:
        return {"label": self.label, "payload_dri": self.payload_dri}

    @classmethod
    async def retrieve_by_id_fully_serialized(cls, context, id):
        record = await cls.retrieve_by_id(context, id)
        oca_schema_data = await load_string(context, record.payload_dri)

        oca_schema_data = json.loads(oca_schema_data)
        record = record.serialize()
        record["oca_schema_data"] = oca_schema_data
        return record


class DefinedConsentRecordSchema(BaseRecordSchema):
    class Meta:
        model_class = "DefinedConsentRecord"

    label = fields.Str(required=True)
    oca_schema = fields.Nested(OcaSchema())
    payload_dri = fields.Str(required=True)


async def routes_retrieve_defined_consent_fully_serialized(context, id):

    try:
        record = await DefinedConsentRecord.retrieve_by_id_fully_serialized(context, id)
    except PersonalDataStorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err)
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err)
    except PersonalDataStorageError as err:
        raise web.HTTPInternalServerError(reason=err)
    except StorageError as err:
        raise web.HTTPInternalServerError(reason=err)

    return record
