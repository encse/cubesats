from io import BytesIO
from datetime import datetime
from sys import argv
from os import path
from typing import NamedTuple

class ImageData(NamedTuple):
    start_row: str
    content: BytesIO
    outputfile: str
    offset: int
    

STRATOSAT_IMAGE_MARKER = "02003E"
STRATOSAT_HIRES_IMAGE_MARKER = "02003E2098"

JPEG_START_MARKER = "FFD8FF"
JPEG_END_MARKER = "FFD9"

def main():

    if len(argv) != 2:
        print(
            f"Usage: {path.basename(argv[0])} <infile>\n"
            "Process Stratosat-TK1 images from Satnogs css export files.\n"
            "You can request an export at https://db.satnogs.org/satellite/BQFG-5755-4293-7808-3570\n"
        )
        exit(0)

    if not path.exists(argv[1]):
        print(f"File not found: {argv[1]}")
        exit(1)

    frames = []
    with open(argv[1], "r") as file:
        for line in file:
            fields = line.strip().split("|")
            created_at = datetime.strptime(fields[0], "%Y-%m-%d %H:%M:%S")
            frame = {"created_at": created_at, "data": fields[1]}
            frames.append(frame)

    get_images(frames)


def get_images(frames):

    image: ImageData = None
    frames = sorted(frames, key=lambda frame: frame["created_at"])
    
    for frame in frames:
        row = frame["data"].upper()

        (header, payload) = (row[:16], row[16:])

        if header.startswith(STRATOSAT_IMAGE_MARKER):
            if payload.startswith(JPEG_START_MARKER):
                if not image or image.start_row != row:
                    if header.startswith(STRATOSAT_HIRES_IMAGE_MARKER):
                        outputfile = "hires-" + frame["created_at"].isoformat() + ".jpg"
                    else:
                        outputfile = frame["created_at"].isoformat() + ".jpg"

                    offset = int.from_bytes(bytes.fromhex(header[10:16]), byteorder="little")

                    image = ImageData(
                        start_row=row, 
                        content=BytesIO(), 
                        outputfile=outputfile,
                        offset=offset
                    )

            if image:
                addr = int.from_bytes(bytes.fromhex(header[10:16]), byteorder="little") - image.offset
                if addr < 0:
                    print(f"{image.outputfile} negative addr {addr}, skipping payload")
                else:
                    image.content.seek(addr)
                    image.content.write(bytes.fromhex(payload))

                    if JPEG_END_MARKER in payload:
                        print(f"Writing {image.outputfile}")
                        with open(image.outputfile, "wb") as f:
                            f.write(image.content.getbuffer())


if __name__ == "__main__":
    main()
