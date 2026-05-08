import uuid
import cloudinary.uploader


def upload_file(file, folder="chat"):

    mime = (file.content_type or "").lower()

    if mime.startswith("image/"):
        resource_type = "image"

    elif mime.startswith("video/"):
        resource_type = "video"

    else:
        resource_type = "raw"

    public_id = str(uuid.uuid4())

    result = cloudinary.uploader.upload(
        file,
        folder=folder,
        resource_type=resource_type,
        type="upload",

        access_control=[
            {"access_type": "anonymous"}
        ],

        public_id=public_id,

        overwrite=False,
    )

    return {
        "url": result.get("secure_url"),
        "public_id": result.get("public_id"),
        "resource_type": result.get("resource_type"),
        "format": result.get("format"),
        "bytes": result.get("bytes"),
        "duration": result.get("duration"),
        "mime_type": mime,
    }