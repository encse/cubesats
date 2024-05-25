from io import BytesIO
from datetime import datetime
from os import path
import os
from typing import NamedTuple, List, Iterable
import argparse
import subprocess

GR_SATELLITES_EXE = "/usr/bin/gr_satellites"
GEOSCAN_IMAGE_MARKERS = ["01003E"] 
JPEG_START_MARKER = "FFD8FF"
JPEG_END_MARKER = "FFD9"

class ImageData(NamedTuple):
    start_row: str
    content: BytesIO
    offset: int

class Frame(NamedTuple):
    created_at: datetime
    data: str

def main():

    parser = argparse.ArgumentParser(
        description="Process Geoscan-Edelveis images.",
        epilog="You can request a csv export at https://db.satnogs.org/satellite/QNCD-8954-6090-5430-2718"
    )
    parser.add_argument('--type', choices=['wav', 'kss', 'hex', 'csv'], help='Type of processing')
    parser.add_argument('file', help='Input file for processing')

    args = parser.parse_args()

    if not path.exists(args.file):
        print(f"File not found: {args.file}")
        exit(1)

    filename_base, extension = path.splitext(args.file)

    if not args.type:
        args.type = extension.lstrip('.')

    if args.type == 'wav':
        frames = parse_wavfile(epoch(), args.file)
    elif args.type == 'kss':
        frames = parse_kissfile(epoch(), args.file)
    elif args.type == 'hex':
        frames = parse_hexfile(epoch(), args.file)
    elif args.type == 'csv':
        frames = parse_cssfile(args.file)
    else:
        print("Invalid processing type specified.")
        exit(1)

    for index, image in enumerate(get_images(frames)):
        filename = filename_base + "-" +  str(index).zfill(5) + ".jpg"
        print(filename)

        with open(filename, "wb") as f:
            f.write(image.content.getbuffer())


def epoch() -> datetime:
   return datetime(1970, 1, 1, 0, 0, 0)

def parse_hexfile(epoch: datetime, f) -> List[Frame]:
    frames = []
    for row in f:
        row = row.replace(' ', '').strip()
        if '|' in row:
            row = row.split('|')[-1]
        if len(row) == 128:
            frame = Frame(created_at=epoch, data=row)
            frames.append(frame)
    return frames


def parse_wavfile(epoch:datetime, f:str) -> List[Frame]:
    filename_base, _ = path.splitext(f)
    kss_file = filename_base+".kss"

    try: 
        result = subprocess.run([GR_SATELLITES_EXE, "GEOSCAN", "--wavfile", f, "--kiss_out", kss_file]) 

        exit_code = result.returncode
        if exit_code != 0:
            print(f'gr_satellites exited with {exit_code}')
            return []

        return parse_kissfile(epoch=epoch, f=kss_file)
    finally:
        os.remove(kss_file)

        
def parse_kissfile(epoch:datetime, f:str) -> List[Frame]:
    frames = []
    file = open(f, "br")
    for row in file.read().split(b'\xc0'):
        if len(row) == 0 or row[0] != 0:
            continue
        
        parsed = row[1:].replace(b'\xdb\xdc', b'\xc0').replace(b'\xdb\xdd', b'\xdb').hex(bytes_per_sep=2)
        if len(parsed) == 128:
            frame = Frame(created_at=epoch, data=parsed)
            frames.append(frame)

    return frames

def parse_cssfile(file:str) -> List[Frame]:
    frames = []
    with open(file, "r") as lines:
        for line in lines:
            fields = line.strip().split("|")
            created_at = datetime.strptime(fields[0], "%Y-%m-%d %H:%M:%S")
            frame = Frame(created_at=created_at, data=fields[1])
            frames.append(frame)
    return frames

def get_images(frames: List[Frame]) -> Iterable[ImageData]:
    image: ImageData = None

    frames = sorted(frames, key=lambda frame: frame.created_at)
    for frame in frames:
        row = frame.data.upper()

        (header, payload) = (row[:16], row[16:])

        if any(header.startswith(marker) for marker in GEOSCAN_IMAGE_MARKERS):
            if payload.startswith(JPEG_START_MARKER):
                if not image or image.start_row != row:
                    if image:
                        yield image
                    offset = int.from_bytes(bytes.fromhex(header[10:14]), byteorder="little")
                    image = ImageData(
                        start_row=row, 
                        content=BytesIO(), 
                        offset=offset,
                    )

            if image:
                addr = int.from_bytes(bytes.fromhex(header[10:14]), byteorder="little")
                addr = addr - image.offset 
                if addr >= 0:
                    image.content.seek(addr)
                    image.content.write(bytes.fromhex(payload))

    if image:
        yield image

if __name__ == "__main__":
    main()
