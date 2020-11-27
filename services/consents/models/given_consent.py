from aries_cloudagent.messaging.models.base_record import BaseRecord, BaseRecordSchema
from marshmallow import fields

from ...models import OcaSchema


class ConsentGivenRecord(BaseRecord):
    RECORD_ID_NAME = "record_id"
    RECORD_TYPE = "given_consent_credential"

    class Meta:
        schema_class = "ConsentGivenRecordSchema"

    def __init__(
        self,
        *,
        consent_user_data_dri: str = None,
        connection_id: str = None,
        credential: dict = None,
        service_consent_match_id: str = None,
        state: str = None,
        record_id: str = None,
        **keyword_args,
    ):
        super().__init__(record_id, state, **keyword_args)
        self.consent_user_data_dri = consent_user_data_dri
        self.connection_id = connection_id
        self.credential = credential
        self.service_consent_match_id = service_consent_match_id

    @property
    def record_value(self) -> dict:
        """Accessor to for the JSON record value properties"""
        return {
            prop: getattr(self, prop)
            for prop in (
                "consent_user_data_dri",
                "connection_id",
                "credential",
                "service_consent_match_id",
            )
        }

    @property
    def record_tags(self) -> dict:
        return {
            "consent_user_data_dri": self.consent_user_data_dri,
            "connection_id": self.connection_id,
            "service_consent_match_id": self.service_consent_match_id,
        }


class ConsentGivenRecordSchema(BaseRecordSchema):
    class Meta:
        model_class = "ConsentGivenRecord"

    oca_schema = fields.Nested(OcaSchema())
    service_consent_match_id = fields.Str(required=True)
    consent_user_data_dri = fields.Str(required=True)
    connection_id = fields.Str(required=True)
    credential = fields.Dict()
