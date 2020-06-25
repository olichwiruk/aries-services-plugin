from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.messaging.models.base_record import BaseRecord, BaseRecordSchema

import hashlib
from marshmallow import fields

class SchemaExchangeRecord(BaseRecord):
    RECORD_TYPE = "SchemaExchange"
    AUTHOR_OTHER = "other"
    AUTHOR_SELF = "self"
    RECORD_ID_NAME = "record_id"

    class Meta:
        schema_class = "SchemaExchangeRecordSchema"

    def __init__(self, *, 
        payload: str, 
        author: str, 
        record_id: str = None, 
        state: str = None, 
        hashid: str = None,
        **kwargs
    ):
        super().__init__(record_id, state, **kwargs)
        self.author = author
        self.payload = payload

        if hashid is None:
            self.hashid = hashlib.sha256(payload.encode("UTF-8")).hexdigest()
        else:
            self.hashid = hashid 


    @property
    def record_tags(self) -> dict:
        return {"hashid": self.hashid}

    @property
    def record_value(self) -> dict:
        """Get record value."""
        return {
            prop: getattr(self, prop)
            for prop in ("payload", "author", "hashid")
        }

    @classmethod
    async def retrieve_by_hashid(
        cls, context: InjectionContext, hashid: str
    ) -> "BasicMessageRecord":
        return await cls.retrieve_by_tag_filter(context, {"hashid": hashid})



class SchemaExchangeRecordSchema(BaseRecordSchema):
    class Meta:
        model_class="SchemaExchange"
    
    author = fields.Str(required=False)
    payload = fields.Str(required=False)
    hashid = fields.Str(required=False)