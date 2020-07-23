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


class ConsentSchema(Schema):
    # dri - decentralized resource identifier
    oca_schema_dri = fields.Str(required=True)
    oca_schema_namespace = fields.Str(required=True)
    data_url = fields.Str(required=True)


class ServiceSchema(Schema):
    oca_schema_dri = fields.Str(required=True)
    oca_schema_namespace = fields.Str(required=True)


class ServiceRecord(BaseRecord):
    RECORD_ID_NAME = "record_id"
    RECORD_TYPE = "verifiable_services"

    class Meta:
        schema_class = "ServiceRecordSchema"

    def __init__(
        self,
        *,
        label: str = None,
        service_schema: str = None,
        consent_schema: str = None,
        state: str = None,
        record_id: str = None,
        **keywordArgs,
    ):
        super().__init__(record_id, state, **keywordArgs)
        self.consent_schema = consent_schema
        self.service_schema = service_schema
        self.label = label

    @property
    def record_value(self) -> dict:
        """Accessor to for the JSON record value properties"""
        return {
            prop: getattr(self, prop)
            for prop in ("service_schema", "consent_schema", "label")
        }

    async def save(
        self,
        context: InjectionContext,
        *,
        reason: str = None,
        log_params: Mapping[str, Any] = None,
        log_override: bool = False,
        webhook: bool = None,
    ) -> str:
        """Persist the record to storage.

        Args:
            context: The injection context to use
            reason: A reason to add to the log
            log_params: Additional parameters to log
            webhook: Flag to override whether the webhook is sent

         NOTE: only deviation from the standard
               is in id generation (hash based)
        """
        new_record = None
        log_reason = reason or ("Updated record" if self._id else "Created record")
        try:
            self.updated_at = time_now()
            storage: BaseStorage = await context.inject(BaseStorage)
            if not self._id:
                record_value = json.dumps(self.record_value)
                self._id = hashlib.sha256(record_value.encode("UTF-8")).hexdigest()
                self.created_at = self.updated_at
                await storage.add_record(self.storage_record)
                new_record = True
            else:
                record = self.storage_record
                await storage.update_record_value(record, record.value)
                await storage.update_record_tags(record, record.tags)
                new_record = False
        finally:
            params = {self.RECORD_TYPE: self.serialize()}
            if log_params:
                params.update(log_params)
            if new_record is None:
                log_reason = f"FAILED: {log_reason}"
            self.log_state(context, log_reason, params, override=log_override)

        await self.post_save(context, new_record, self._last_state, webhook)
        self._last_state = self.state

        return self._id


class ServiceRecordSchema(BaseRecordSchema):
    class Meta:
        model_class = "ServiceRecord"

    label = fields.Str(required=True)
    service_schema = fields.Nested(ServiceSchema())
    consent_schema = fields.Nested(ConsentSchema())


class ServiceDiscoveryRecord(BaseRecord):
    RECORD_ID_NAME = "record_id"
    RECORD_TYPE = "service_discovery"

    class Meta:
        schema_class = "ServiceDiscoveryRecordSchema"

    def __init__(
        self,
        *,
        services=None,
        connection_id: str = None,
        state: str = None,
        record_id: str = None,
        **keywordArgs,
    ):
        super().__init__(record_id, state, **keywordArgs)
        self.services = services
        self.connection_id = connection_id

    @property
    def record_value(self) -> dict:
        """Accessor to for the JSON record value properties"""
        return {prop: getattr(self, prop) for prop in ("services", "connection_id")}

    @property
    def record_tags(self) -> dict:
        """Get tags for record, 
            NOTE: relevent when filtering by tags"""
        return {
            "connection_id": self.connection_id,
        }

    @classmethod
    async def retrieve_by_connection_id(
        cls, context: InjectionContext, connection_id: str
    ):
        return await cls.retrieve_by_tag_filter(
            context, {"connection_id": connection_id},
        )

    async def save(
        self,
        context: InjectionContext,
        *,
        reason: str = None,
        log_params: Mapping[str, Any] = None,
        log_override: bool = False,
        webhook: bool = None,
    ) -> str:
        """Persist the record to storage.

        Args:
            context: The injection context to use
            reason: A reason to add to the log
            log_params: Additional parameters to log
            webhook: Flag to override whether the webhook is sent

         NOTE: only deviation from the standard
               is in id generation (hash based)
        """
        new_record = None
        log_reason = reason or ("Updated record" if self._id else "Created record")
        try:
            self.updated_at = time_now()
            storage: BaseStorage = await context.inject(BaseStorage)
            if not self._id:
                id_base = json.dumps(self.connection_id)
                self._id = hashlib.sha256(id_base.encode("UTF-8")).hexdigest()
                self.created_at = self.updated_at
                await storage.add_record(self.storage_record)
                new_record = True
            else:
                record = self.storage_record
                await storage.update_record_value(record, record.value)
                await storage.update_record_tags(record, record.tags)
                new_record = False
        finally:
            params = {self.RECORD_TYPE: self.serialize()}
            if log_params:
                params.update(log_params)
            if new_record is None:
                log_reason = f"FAILED: {log_reason}"
            self.log_state(context, log_reason, params, override=log_override)

        await self.post_save(context, new_record, self._last_state, webhook)
        self._last_state = self.state

        return self._id

