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

from ..discovery.models import ConsentSchema, ServiceSchema
from ..util import assert_items_are_not_none


class ServiceIssueRecord(BaseRecord):
    RECORD_ID_NAME = "record_id"
    RECORD_TYPE = "service_issue"

    ISSUE_WAITING_FOR_RESPONSE = "waiting for response"
    ISSUE_PENDING = "pending issue"
    ISSUE_REJECTED = "rejected issue"
    ISSUE_ACCEPTED = "accepted issue"

    AUTHOR_SELF = "self"
    AUTHOR_OTHER = "other"

    class Meta:
        schema_class = "ServiceIssueRecordSchema"

    def __init__(
        self,
        *,
        state: str = None,
        author: str = None,
        service_schema: ServiceSchema = None,
        consent_schema: ConsentSchema = None,
        connection_id: str = None,
        exchange_id: str = None,
        record_id: str = None,
        **keywordArgs,
    ):
        super().__init__(record_id, state, **keywordArgs)
        self.service_schema = service_schema
        self.consent_schema = consent_schema
        self.connection_id = connection_id
        self.author = author
        self.exchange_id = str(uuid.uuid4()) if exchange_id is None else exchange_id

    @property
    def record_value(self) -> dict:
        """Accessor to for the JSON record value properties"""
        return {
            prop: getattr(self, prop)
            for prop in (
                "service_schema",
                "consent_schema",
                "connection_id",
                "state",
                "author",
                "exchange_id",
            )
        }

    @property
    def unique_record_values(self) -> dict:
        """Hash id of a record is based on those values"""
        return {prop: getattr(self, prop) for prop in ("connection_id", "exchange_id",)}

    @property
    def record_tags(self) -> dict:
        """Get tags for record, 
            NOTE: relevent when filtering by tags"""
        return {
            "connection_id": self.connection_id,
            "exchange_id": self.exchange_id,
            "state": self.state,
            "author": self.author,
        }

    @classmethod
    async def retrieve_by_exchange_id_and_connection_id(
        cls, context: InjectionContext, exchange_id: str, connection_id: str
    ):
        return await cls.retrieve_by_tag_filter(
            context, {"exchange_id": exchange_id, "connection_id": connection_id},
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
                # NOTE: only change here, calculating id
                unique_record_value = json.dumps(self.unique_record_values)
                print(unique_record_value)
                self._id = hashlib.sha256(
                    unique_record_value.encode("UTF-8")
                ).hexdigest()

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


class ServiceIssueRecordSchema(BaseRecordSchema):
    class Meta:
        model_class = "ServiceIssueRecord"

    state = fields.Str(required=False)
    author = fields.Str(required=False)
    connection_id = fields.Str(required=False)
    exchange_id = fields.Str(required=False)
    service_schema = fields.Nested(ServiceSchema())
    consent_schema = fields.Nested(ConsentSchema())
