from aiohttp import web

from .issue.routes import *
from .discovery.routes import *

# NOTE: define functions in sub routes files (i.e issue.routes) and register
# them here


async def register(app: web.Application):
    app.add_routes(
        [
            web.post("/verifiable-services/add", add_service),
            web.post("/verifiable-services/apply", apply),
            web.get(
                "/verifiable-services/request-list/{connection_id}",
                request_services_list,
                allow_head=False,
            ),
            web.get(
                "/verifiable-services/get-list/{connection_id}",
                get_service_list,
                allow_head=False,
            ),
        ]
    )
