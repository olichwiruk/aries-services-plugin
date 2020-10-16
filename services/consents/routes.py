from aiohttp import web
from aiohttp_apispec import docs, request_schema

from marshmallow import fields, Schema
from ..models import OcaSchema
from .models.defined_consent import DefinedConsentRecord


class AddConsentSchema(Schema):
    label = fields.Str(required=True)
    oca_schema = fields.Nested(OcaSchema())
    payload = fields.Dict(required=True)


@request_schema(AddConsentSchema())
@docs(tags=["Defined Consents"], summary="Add consent definition")
async def add_consent(request: web.BaseRequest):
    context = request.app["request_context"]
    params = await request.json()
    errors = []

    existing_consents = await DefinedConsentRecord.query(
        context, {"label": params["label"]}
    )
    if existing_consents:
        errors.append(
            f"Consent with '{params['label']}' label is already defined"
        )

    if errors:
        return web.json_response({"success": False, "errors": errors})
    else:
        defined_consent = DefinedConsentRecord(
            label=params["label"],
            oca_schema=params["oca_schema"],
            payload_dri=''
        )

        await defined_consent.save(context)

        return web.json_response({"success": True})
