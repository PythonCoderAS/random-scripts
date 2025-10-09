from asyncio import gather
from pathlib import Path
from typing import Annotated

from typer import Argument, Option
from ..app import app
from os import getenv, scandir
from .utils import JellyfinAPIClient


@app.command()
async def add_all_subdirectories_to_library(
    library_name: str,
    parent_folder_path: Annotated[
        Path,
        Argument(
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
            help="The parent folder containing subdirectories to add to the Jellyfin library.",
        ),
    ],
    jellyfin_server_url: str = getenv("JELLYFIN_SERVER_URL", "http://localhost:8096"),
    api_key: str | None = getenv("JELLYFIN_API_KEY"),
    path_replace_from: str | None = Option(
        default=None,
        help="A substring in the folder paths to replace. Useful for adjusting paths when the server sees them differently.",
    ),
    path_replace_to: str | None = Option(
        default=None,
        help="The substring to replace with in the folder paths.",
    ),
):
    """Add all subdirectories of a given parent folder to a specified Jellyfin library.

    :param library_name: The name of the Jellyfin library to which subdirectories will be added. Must exist and match casing.
    :param parent_folder_path: The parent folder containing subdirectories to add to the Jellyfin library.
    :param jellyfin_server_url: The base URL of the Jellyfin server, defaults to the JELLYFIN_SERVER_URL environment variable or "http://localhost:8096"
    :param api_key: The API key for authenticating with the Jellyfin server, defaults to the JELLYFIN_API_KEY environment variable
    :param path_replace_from: A substring in the folder paths to replace. Useful for adjusting paths when the server sees them differently.
    :param path_replace_to: The substring to replace with in the folder paths.
    :raises ValueError: If the API key is not provided or if only one of the path replacement parameters is provided.
    """
    if not api_key:
        raise ValueError(
            "JELLYFIN_API_KEY environment variable must be set or the --api-key option must be provided."
        )
    if (path_replace_from and not path_replace_to) or (
        path_replace_to and not path_replace_from
    ):
        raise ValueError(
            "Both --path-replace-from and --path-replace-to must be provided together."
        )
    paths = {
        dir.path.replace(path_replace_from, path_replace_to)
        if (path_replace_from and path_replace_to)
        else dir.path
        for dir in scandir(parent_folder_path)
        if dir.is_dir()
    }
    async with JellyfinAPIClient(jellyfin_server_url, api_key=api_key) as session:
        existing_libraries = await session.get_libraries()
        library = next(
            (lib for lib in existing_libraries if lib.Name == library_name), None
        )
        if not library:
            raise ValueError(f"Library with name '{library_name}' not found.")
        existing_paths = set(library.Locations)
        new_paths = paths - existing_paths
        if not new_paths:
            print("No new subdirectory paths to add, exiting.")
            return
        else:
            last_path = new_paths.pop()
            await gather(
                *[
                    session.add_path_to_library(
                        library.Name, path, refresh_library=False
                    )
                    for path in new_paths
                ]
            )
            await session.add_path_to_library(
                library.Name, last_path, refresh_library=True
            )
            print(f"Added {len(paths)} new paths to library '{library.Name}'.")
