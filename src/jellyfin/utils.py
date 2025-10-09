"""Utility functions for working with the Jellyfin API."""

from typing import TYPE_CHECKING, Self
from urllib.parse import quote
from aiohttp import ClientSession
from pydantic import BaseModel, RootModel


class Library(BaseModel):
    """Represents a Jellyfin library. Does not include all fields."""

    Name: str
    Locations: list[str]


class JellyfinAPIClient(ClientSession):
    """Client for interacting with the Jellyfin API."""

    def __init__(self, base_url: str, *, api_key: str):
        """Initialize the Jellyfin API client."""
        super().__init__(base_url)
        self.headers.update(
            {
                "Authentication": f'MediaBrowser Token="{quote(api_key)}", Client="RandomScripts", Version="1.0", Device="PythonClient", DeviceId="PythonClient"'
            }
        )

    async def get_libraries(self) -> list[Library]:
        """Get a list of libraries from the Jellyfin server."""
        async with self.get("/Library/VirtualFolders") as response:
            response.raise_for_status()
            data = await response.json()
            return RootModel[list[Library]].model_validate(data).root

    async def add_path_to_library(
        self, library_name: str, folder_path: str, refresh_library: bool = False
    ) -> None:
        body = {"Name": library_name, "PathInfo": {"Path": folder_path}}
        params = {"refreshLibrary": str(refresh_library).lower()}
        async with self.post(
            "/Library/VirtualFolders/Paths", params=params, json=body
        ) as response:
            response.raise_for_status()

    if TYPE_CHECKING:

        async def __aenter__(self) -> Self: ...
