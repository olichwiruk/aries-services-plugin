from aiohttp import web
from aiohttp_apispec import docs, request_schema

from marshmallow import fields, Schema
import json

from aries_cloudagent.pdstorage_thcf.api import save_string, load_string
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
        payload_dri = await save_string(context, json.dumps(params["payload"]))
        defined_consent = DefinedConsentRecord(
            label=params["label"],
            oca_schema=params["oca_schema"],
            payload_dri=payload_dri
        )

        await defined_consent.save(context)

        return web.json_response({"success": True})


@docs(tags=["Defined Consents"], summary="Get all consent definitions")
async def get_consents(request: web.BaseRequest):
    context = request.app["request_context"]

    all_consents = await DefinedConsentRecord.query(context, {})
    result = list(map(lambda el: el.record_value, all_consents))
    for consent in result:
        payload = await load_string(context, consent["payload_dri"])
        if payload:
            consent["payload"] = json.loads(payload)
        else:
            consent["payload"] = None

    return web.json_response({"success": True, "result": result})
