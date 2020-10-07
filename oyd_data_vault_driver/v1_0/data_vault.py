from aries_cloudagent.public_data_storage_thcf.base import PublicDataStorage
from aries_cloudagent.public_data_storage_thcf.error import *

import json

from aiohttp import ClientSession, FormData

API_DATA_VAULT = "https://data-vault.eu"
API_TOKEN = API_DATA_VAULT + "/oauth/token"
API_ON_SAVE = API_DATA_VAULT + "/api/repos/dip.data/items"
API_ON_READ = API_DATA_VAULT + "/api/items"

# "https://data-vault.eu/api/repos/dip.data/items"
# TOKEN
# {
#   "access_token":"1234",
#   "token_type":"Bearer",
#   "expires_in":7200,
#   "created_at":1601638565,
#   "username":"Karol"
# }
# SAVE return json
# {"id":1609914}


class OYDDataVault(PublicDataStorage):
    def __init__(self):
        super().__init__()
        self.token = None
        self.settings = {
            "client_id": "1234-example",
            "client_secret": "1234-example",
            "grant_type": "client_credentials",
        }

    async def update_token(self):
        # TODO: Add timestamp check because token expires
        # if self.token != None:
        #     return
        client_id = self.settings.get("client_id")
        client_secret = self.settings.get("client_secret")

        if client_id == None:
            raise PublicDataStorageLackingConfigurationError(
                "Please configure the plugin, Client_id is empty"
            )
        if client_secret == None:
            raise PublicDataStorageLackingConfigurationError(
                "Please configure the plugin, Client_secret is empty"
            )

        async with ClientSession() as session:
            result = await session.post(
                API_TOKEN,
                json={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "client_credentials",
                },
            )
            if result.status != 200:
                raise PublicDataStorageServerError(
                    "Server Error, Could be that the connection is invalid or some other unforseen error, check if the server is up"
                )

            result = await result.text()
            token = json.loads(result)
            self.token = token
            print("self.token", self.token)

    async def load(self, id: str) -> str:
        """
        TODO: Errors checking
        """
        await self.update_token()
        async with ClientSession() as session:
            result = await session.get(
                f"{API_ON_READ}/{id}/details",
                headers={"Authorization": "Bearer " + self.token["access_token"]},
            )
            result = await result.text()
            result = json.loads(result)
            print(result)

        return result["value"]["payload"]

    async def save(self, record: str) -> str:
        await self.update_token()
        async with ClientSession() as session:
            result = await session.post(
                "https://data-vault.eu/api/repos/dip.data/items",
                json={"payload": record},
                headers={"Authorization": "Bearer " + self.token["access_token"]},
            )
            result = await result.text()
            result = json.loads(result)

        return result.get("id")