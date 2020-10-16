from aiohttp import web
from aiohttp_apispec import docs, request_schema

from marshmallow import fields, Schema
from ..models import OcaSchema


class AddConsentSchema(Schema):
    label = fields.Str(required=True)
    oca_schema = fields.Nested(OcaSchema())
    payload = fields.Dict(required=True)


@request_schema(AddConsentSchema())
@docs(tags=["Defined Consents"], summary="Add consent definition")
async def add_consent(request: web.BaseRequest):

    return web.json_response('hello world!')
