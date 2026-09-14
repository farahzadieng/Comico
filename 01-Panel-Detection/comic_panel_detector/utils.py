import re
from pathlib import Path


SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp"
}



def natural_sort_key(text):

    return [
        int(x) if x.isdigit() else x.lower()

        for x in re.split(
            r"(\d+)",
            text
        )
    ]



def discover_images(directory):

    directory = Path(directory)


    if not directory.exists():

        raise FileNotFoundError(
            f"Input directory not found: {directory}"
        )


    images = []


    for file in directory.iterdir():

        if (
            file.is_file()
            and file.suffix.lower()
            in SUPPORTED_EXTENSIONS
        ):
            images.append(file)


    return sorted(
        images,
        key=lambda x:
        natural_sort_key(x.name)
    )



def clamp(value, minimum, maximum):

    return max(
        minimum,
        min(
            value,
            maximum
        )
    )



def validate_bbox(
        x1,
        y1,
        x2,
        y2,
        width,
        height
):

    x1 = clamp(x1,0,width)
    x2 = clamp(x2,0,width)

    y1 = clamp(y1,0,height)
    y2 = clamp(y2,0,height)


    if x2 <= x1 or y2 <= y1:
        return None


    return (
        int(x1),
        int(y1),
        int(x2),
        int(y2)
    )