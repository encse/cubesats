from io import BytesIO
from datetime import datetime
from sys import argv
from os import path

STRATOSAT_IMAGE_MARKER = "02003E"
STRATOSAT_HIHGRES_IMAGE_MARKER = "02003E2098"

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
    frames = sorted(frames, key=lambda frame: frame["created_at"])

    current_image = None
    current_header = ""
    current_offset = 0

    for frame in frames:
        row = frame["data"].upper()

        (header, payload) = (row[:16], row[16:])

        if header.startswith(STRATOSAT_IMAGE_MARKER):
            if payload.startswith(JPEG_START_MARKER):

                if current_header != header:
                    current_image = BytesIO()
                    current_header = header
                    current_offset = int.from_bytes(bytes.fromhex(header[10:16]), byteorder="little")

                    if header.startswith(STRATOSAT_HIHGRES_IMAGE_MARKER):
                        outfile = "hires-" + frame["created_at"].isoformat() + ".jpg"
                    else:
                        outfile = frame["created_at"].isoformat() + ".jpg"

            addr = int.from_bytes(bytes.fromhex(header[10:16]), byteorder="little") - current_offset

            if not current_image:
                print("Missing .jpg start block, skipping")
            elif addr < 0:
                print(f"{outfile} negative addr {addr}, skipping payload")
            else:
                current_image.seek(addr)
                current_image.write(bytes.fromhex(payload))

                if JPEG_END_MARKER in payload:
                    print(f"Writing {outfile}")
                    with open(outfile, "wb") as f:
                        f.write(current_image.getbuffer())


if __name__ == "__main__":

    main()
