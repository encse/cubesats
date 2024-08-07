from io import BytesIO
from datetime import datetime
from os import path
import os
from typing import NamedTuple, List, Iterable
import argparse
import subprocess

GR_SATELLITES_EXE = "/usr/bin/gr_satellites"
STRATOSAT_IMAGE_MARKER = "02003E"
JPEG_START_MARKER = "FFD8FF"
JPEG_END_MARKER = "FFD9"

class ImageData(NamedTuple):
    filename: str
    start_row: str
    content: BytesIO
    offset: int

class Frame(NamedTuple):
    created_at: datetime
    data: str

def main():

    parser = argparse.ArgumentParser(
        description="Process Stratosat-TK1 images.",
        epilog="You can request a csv export at https://db.satnogs.org/satellite/BQFG-5755-4293-7808-3570",
    )
    parser.add_argument('--type', choices=['wav', 'kss', 'hex', 'csv'], help='Type of processing')
    parser.add_argument('--single', action=argparse.BooleanOptionalAction, help='combine all data into a single image')
    parser.add_argument('--out', required=False, default='', help='output directory')
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

    if args.single:
        print("single image mode")
        image_provider = get_single_image
    else:
        print("multiple image mode")
        image_provider = get_images

    any_image = False
    for _, image in enumerate(image_provider(frames, path.join(args.out, filename_base))):
        any_image = True
        with open(image.filename, "wb") as f:
            f.write(image.content.getbuffer())

        print(f"💾 {image.filename} saved")

    if not any_image:
        print("🤷 could not find jpg header")


def epoch() -> datetime:
   return datetime(1970, 1, 1, 0, 0, 0)

def parse_hexfile(epoch: datetime, f) -> List[Frame]:
    frames = []
    for row in open(f, "r"):
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
        result = subprocess.run([GR_SATELLITES_EXE, "STRATOSAT-TK1", "--wavfile", f, "--kiss_out", kss_file]) 

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

def get_single_image(frames: List[Frame], filename_base: str) -> Iterable[ImageData]:
    image: ImageData = None
    frames = sorted(frames, key=lambda frame: frame.created_at)
    index = 0
    for frame in frames:
        row = frame.data.upper()

        (header, payload) = (row[:16], row[16:])

        if header.startswith(STRATOSAT_IMAGE_MARKER):
            if payload.startswith(JPEG_START_MARKER):
                print("🎲 Found jpeg header")
                offset = int.from_bytes(
                    bytes.fromhex(header[10:16]), byteorder="little"
                )
        
                filename =  filename_base + "-" +  str(index).zfill(5) + ".jpg"
                image = ImageData(
                    filename=filename,
                    start_row=row,
                    content=BytesIO(),
                    offset=offset,
                )
                break

    if image:
        print("🛰  processing all frames with the header now")
        for frame in frames:
            row = frame.data.upper()
            (header, payload) = (row[:16], row[16:])
            addr = int.from_bytes(bytes.fromhex(header[10:16]), byteorder="little")
            addr = addr - image.offset 
            if addr >= 0:
                image.content.seek(addr)
                image.content.write(bytes.fromhex(payload))
       
        yield image

def get_images(frames: List[Frame], filename_base: str) -> Iterable[ImageData]:
    image: ImageData = None
    frames = sorted(frames, key=lambda frame: frame.created_at)
    index = 0
    for frame in frames:
        row = frame.data.upper()

        (header, payload) = (row[:16], row[16:])

        if header.startswith(STRATOSAT_IMAGE_MARKER):
            if payload.startswith(JPEG_START_MARKER):
                if not image or image.start_row != row:

                    if image:
                        yield image

                    offset = int.from_bytes(
                        bytes.fromhex(header[10:16]), byteorder="little"
                    )

            
                    filename =  filename_base + "-" +  str(index).zfill(5) + ".jpg"
                    index+=1
                    print(f"🎲 Found jpeg header")
                    print(f"🛰 {filename} transmission")
                    image = ImageData(
                        filename=filename,
                        start_row=row,
                        content=BytesIO(),
                        offset=offset,
                    )
                else:
                    print(f"🛰 {filename} retransmit")

            if image:
                addr = int.from_bytes(bytes.fromhex(header[10:16]), byteorder="little")
                addr = addr - image.offset 
                if addr >= 0:
                    image.content.seek(addr)
                    image.content.write(bytes.fromhex(payload))

    if image:
        yield image


if __name__ == "__main__":
    main()
