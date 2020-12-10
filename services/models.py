from aries_cloudagent.messaging.models.base_record import BaseRecord, BaseRecordSchema
from aries_cloudagent.storage.base import BaseStorage
from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.storage.error import StorageDuplicateError
from aries_cloudagent.messaging.util import datetime_to_str, time_now

import hashlib
from marshmallow import fields, Schema
from typing import Mapping, Any
import uuid
import json


class ConsentContentSchema(Schema):
    expiration = fields.Str(required=True)
    limitation = fields.Str(required=True)
    dictatedBy = fields.Str(required=True)
    validityTTL = fields.Str(required=True)


class ConsentSchema(Schema):
    # dri - decentralized resource identifier
    oca_schema_dri = fields.Str(required=False)
    oca_schema_namespace = fields.Str(required=False)
    data_dri = fields.Str(required=False)
    data = fields.Str(required=False)


class ServiceSchema(Schema):
    oca_schema_dri = fields.Str(required=False)
    oca_schema_namespace = fields.Str(required=False)


class OcaSchema(Schema):
    namespace = fields.Str(required=False)
    dri = fields.Str(required=False)


class ServiceRecord(BaseRecord):
    RECORD_ID_NAME = "record_id"
    RECORD_TYPE = "verifiable_services"

    class Meta:
        schema_class = "ServiceRecordSchema"

    def __init__(
        self,
        *,
        label: str = None,
        service_schema: ServiceSchema = None,
        consent_schema: ConsentSchema = None,
        appliance_policy: str = None,
        state: str = None,
        record_id: str = None,
        **keyword_args,
    ):
        super().__init__(record_id, state, **keyword_args)
        self.consent_schema = consent_schema
        self.service_schema = service_schema
        self.appliance_policy = appliance_policy
        self.label = label

    @property
    def record_value(self) -> dict:
        """Accessor to for the JSON record value properties"""
        return {
            prop: getattr(self, prop)
            for prop in (
                "service_schema",
                "consent_schema",
                "label",
                "appliance_policy",
            )
        }

    @property
    def record_tags(self) -> dict:
        return {"label": self.label}


class ServiceRecordSchema(BaseRecordSchema):
    class Meta:
        model_class = "ServiceRecord"

    label = fields.Str(required=True)
    service_id = fields.Str(required=True)
    service_schema = fields.Nested(ServiceSchema())
    consent_schema = fields.Nested(ConsentSchema())
    appliance_policy = fields.Str(required=True)
