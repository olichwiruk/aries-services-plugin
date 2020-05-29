from .message_types import *
from .util import generate_model_schema
from marshmallow import fields

HANDLERS = f"{PROTOCOL_PACKAGE}.handlers"
ADD_HANDLER = f"{HANDLERS}.RecordsAddHandler"
GET_HANDLER = f"{HANDLERS}.RecordsGetHandler"

RecordsAdd, RecordsAddSchema = generate_model_schema(
    name="RecordsAdd",
    handler=ADD_HANDLER,
    msg_type=ADD,
    schema={
        "payload": fields.Str(required=True),
        "hashid": fields.Str(required=False),
    },
)


RecordsGet, RecordsGetSchema = generate_model_schema(
    name="RecordsGet",
    handler=GET_HANDLER,
    msg_type=GET,
    schema={
        "hashid": fields.Str(required=True),
        "payload": fields.Str(required=False),
    },
)
