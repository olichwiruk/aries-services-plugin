from aiohttp import web
from aiohttp_apispec import docs, request_schema

from marshmallow import fields, Schema
import json

from aries_cloudagent.pdstorage_thcf.api import *
from aries_cloudagent.storage.error import StorageError
from ..models import OcaSchema
from .models.defined_consent import DefinedConsentRecord
from .models.given_consent import ConsentGivenRecord
from ..models import ConsentSchema

CONSENTS_TABLE = "consents"


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

    try:
        existing_consents = await DefinedConsentRecord.query(
            context, {"label": params["label"]}
        )
    except StorageError as err:
        raise web.HTTPInternalServerError(reason=err)

    if existing_consents:
        errors.append(f"Consent with '{params['label']}' label is already defined")

    if errors:
        return web.json_response({"success": False, "errors": errors})
    else:
        metadata = {
            "oca_schema_dri": params["oca_schema"]["dri"],
            "table": CONSENTS_TABLE,
        }

        """
        If pds supports usage policy then pack it into consent
        """

        schema = {}
        consent_user_data = params["payload"]
        # pds_usage_policy = await pds_get_usage_policy_if_active_pds_supports_it(context)
        # if pds_usage_policy is not None:
        #     consent_user_data["usage_policy"] = pds_usage_policy
        #     schema["usage_policy"] = pds_usage_policy

        payload_dri = await save_string(
            context, json.dumps(consent_user_data), json.dumps(metadata)
        )

        defined_consent = DefinedConsentRecord(
            label=params["label"],
            oca_schema=params["oca_schema"],
            payload_dri=payload_dri,
        )

        consent_id = await defined_consent.save(context)

        schema["oca_schema_dri"] = params["oca_schema"]["dri"]
        schema["oca_schema_namespace"] = params["oca_schema"]["namespace"]
        schema["data_dri"] = payload_dri

        return web.json_response({"success": True, "schema": schema})


@docs(tags=["Defined Consents"], summary="Get all consent definitions")
async def get_consents(request: web.BaseRequest):
    context = request.app["request_context"]

    try:
        all_consents = await DefinedConsentRecord.query(context, {})
    except StorageError as err:
        raise web.HTTPInternalServerError(reason=err)

    result = list(map(lambda el: el.record_value, all_consents))
    for consent in result:
        payload = await load_string(context, consent["payload_dri"])
        print("PAYLOAD: ", payload)
        if payload:
            consent["payload"] = json.loads(payload)
        else:
            consent["payload"] = None

    return web.json_response({"success": True, "result": result})


@docs(
    tags=["Defined Consents"],
    summary="Get all the consents I have given to other people",
)
async def get_consents_given(request: web.BaseRequest):
    context = request.app["request_context"]

    try:
        all_consents = await ConsentGivenRecord.query(context)
    except StorageError as err:
        raise web.HTTPInternalServerError(reason=err)
    serialized = [i.serialize() for i in all_consents]

    return web.json_response({"success": True, "result": serialized})
