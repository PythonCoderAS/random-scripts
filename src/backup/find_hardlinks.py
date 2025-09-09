from .. import app

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from sys import stdout
from pathlib import Path


def add_file_inode_to_map(
    file_path: Path,
    inode_map: dict[Path, int],
    seen_inodes_map: defaultdict[int, list[Path]],
):
    try:
        inode = file_path.stat().st_ino
        inode_map[file_path] = inode
        seen_inodes_map[inode].append(file_path)
    except FileNotFoundError:
        pass


def check_if_file_is_hardlink(
    file_path: Path,
    paths_per_inode: defaultdict[int, list[Path]],
    *,
    skip_symlinks: bool,
    originals_directory_path: Path,
):
    try:
        if file_path.is_symlink():
            if skip_symlinks:
                return
            else:
                file_path = file_path.resolve()
        if file_path.is_relative_to(originals_directory_path):
            return
        inode = file_path.stat().st_ino
        if inode in paths_per_inode:
            paths_per_inode[inode].append(file_path)
    except FileNotFoundError:
        pass


@app.command()
def find_hardlinks(
    root_directory: Path,
    originals_directory: Path,
    min_links: int = 1,
    to_file: Path | None = None,
    append_to_file: bool = True,
    skip_symlinks: bool = True,
    include_originals_in_output: bool = False,
    skip_directories: list[Path] = [],
):
    """Find all files in the root directory that are hardlinks to files in the originals directory.

    :param root_directory: The root directory to search for hardlinks.

    :param originals_directory: The directory containing the original files. If the originals directory is a subdirectory of the root directory, it will not be counted when doing the search.

    :param min_links: How many additional links need to exist outside of the source file, defaults to 1

    :param to_file: Write results to this file, defaults to stdout if not provided

    :param append_to_file: Append to the file if it exists, otherwise overwrite it, defaults to True

    :param skip_symlinks: Skip symbolic links when searching for hardlinks, defaults to True. If symlinks are not skipped, they will be counted as hardlinks if they point to a file in the originals directory. This does not affect symlinks in the originals directory.

    :param include_originals_in_output: Include the original files in the output, defaults to False. If True, the original files will be included in the output if they have at least `min_links` hardlinks outside of the originals directory.

    :param skip_directories: List of directories to skip when searching for hardlinks, defaults to [].
    """
    if min_links < 1:
        raise ValueError("min_links must be at least 1")
    if to_file is None:
        output_file = stdout
    else:
        if append_to_file:
            output_file = open(to_file, "a")
        else:
            output_file = open(to_file, "w")
    root_directory_path = root_directory.absolute()
    originals_directory_path = originals_directory.absolute()
    originals_inode_map: dict[Path, int] = {}
    paths_per_inode: defaultdict[int, list[Path]] = defaultdict(list)
    with ThreadPoolExecutor() as executor:
        for path, _, files in originals_directory_path.walk():
            for file in files:
                file_path = path / file
                executor.submit(
                    add_file_inode_to_map,
                    file_path,
                    originals_inode_map,
                    paths_per_inode,
                )
    with ThreadPoolExecutor() as executor:
        for path, _, files in root_directory_path.walk():
            if any(path.is_relative_to(skip_dir) for skip_dir in skip_directories):
                continue
            for file in files:
                file_path = path / file
                executor.submit(
                    check_if_file_is_hardlink,
                    file_path,
                    paths_per_inode,
                    skip_symlinks=skip_symlinks,
                    originals_directory_path=originals_directory_path,
                )
    for paths in paths_per_inode.values():
        # Due to the structure, the original file will always be the first one in the list
        original_file = paths[0]
        if len(paths) - 1 >= min_links:
            if include_originals_in_output:
                print(original_file, file=output_file)
            for i in range(1, len(paths)):
                print(paths[i], file=output_file)
