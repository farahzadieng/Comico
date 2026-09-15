import re
from pathlib import Path
from typing import List


SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}


def natural_sort_key(text: str):
    return [
        int(x) if x.isdigit() else x.lower()
        for x in re.split(r"(\d+)", text)
    ]


def discover_images(directory) -> List[Path]:
    """
    Discover supported images directly inside one directory.

    This function is intentionally non-recursive. In recursive/batch mode,
    each image-containing directory is treated as an independent collection.
    """
    directory = Path(directory)

    if not directory.exists():
        raise FileNotFoundError(
            f"Input directory not found: {directory}"
        )

    if not directory.is_dir():
        raise NotADirectoryError(
            f"Input path is not a directory: {directory}"
        )

    images = [
        file
        for file in directory.iterdir()
        if file.is_file()
        and file.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    return sorted(
        images,
        key=lambda x: natural_sort_key(x.name)
    )


def discover_comic_directories(root_directory) -> List[Path]:
    """
    Recursively discover image collections under root_directory.

    Every directory that directly contains at least one supported image is
    returned as one independent collection. Images from different directories
    are never merged into the same page sequence.
    """
    root = Path(root_directory)

    if not root.exists():
        raise FileNotFoundError(
            f"Input directory not found: {root}"
        )

    if not root.is_dir():
        raise NotADirectoryError(
            f"Input path is not a directory: {root}"
        )

    candidates = [root]
    candidates.extend(
        path for path in root.rglob("*")
        if path.is_dir()
    )

    collections = []

    for directory in candidates:
        has_images = any(
            file.is_file()
            and file.suffix.lower() in SUPPORTED_EXTENSIONS
            for file in directory.iterdir()
        )

        if has_images:
            collections.append(directory)

    def collection_sort_key(directory: Path):
        if directory == root:
            relative = "."
        else:
            relative = directory.relative_to(root).as_posix()

        return natural_sort_key(relative)

    return sorted(
        collections,
        key=collection_sort_key
    )


def clamp(value, minimum, maximum):
    return max(
        minimum,
        min(value, maximum)
    )


def validate_bbox(
    x1,
    y1,
    x2,
    y2,
    width,
    height
):
    x1 = clamp(x1, 0, width)
    x2 = clamp(x2, 0, width)

    y1 = clamp(y1, 0, height)
    y2 = clamp(y2, 0, height)

    if x2 <= x1 or y2 <= y1:
        return None

    return (
        int(x1),
        int(y1),
        int(x2),
        int(y2)
    )
