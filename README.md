# Bulk decoder for Stratosat TK-1 and Geoscan-Edelveis imagery

This tool decodes images received from Stratosat TK-1 / Geoscan-Edelveis satellites. Supported formats are: wav audio, kss, hex dump and
csv files exported from the Satnogs database.

![](images/2024-03-09T08:25:47.jpg)

You can request a csv from https://db.satnogs.org/satellite/BQFG-5755-4293-7808-3570. 

Save it to something like BQFG-5755-4293-7808-3570-3524-20240310T132149Z-week.csv.


## Dockerized usage

You need to build the container first
```
> docker build -t cubesats  .
```

Then invoke with:
```
> docker run --rm -v `pwd`:/data cubesats /app/stratosat.py --type=wav audio_434957996Hz_10-41-34_25-05-2024.wav
```

or use the provided shell script
```
> ./stratosat.sh --type=wav audio_434957996Hz_10-41-34_25-05-2024.wav
```


This command will spin up a docker container for you, invoke stratrosat.py with the wav file you specify. `gr-satellites` is used to extract the `kss` frames from the audio, then the image(s) will be placed next to the `wav` file. The input file should be in the current directory (or you need to adjust the volume mapping).

## Direct usage

```
> python3 stratosat.py BQFG-5755-4293-7808-3570-3524-20240310T132149Z-week.csv
```

The csv file has the format:

```
2024-03-10 09:53:03|848A82869E9C60A4A66A64A640E103F00B83ED659305D810F0EBCBEB5D0A00004A04000004F7F11F80FF00000111590189000161339987000000000000000000||SONIKS: Station_22-KO04hr
2024-03-10 09:52:30|848A82869E9C60A4A66A64A640E103F0EA82ED659205FB10F0EBC9EB5D0A00004A04000005F6F01E80FF00000110590189000161339887000000000000000000||SONIKS: Station_22-KO04hr
2024-03-10 09:51:58|848A82869E9C60A4A66A64A640E103F0CA82ED6598088A16F0EBC7EB5D0A00004A04000007F5F01D80FE00000111590189000161339787000000000000000000||SONIKS: Station_22-KO04hr
2024-03-10 09:50:52|848A82869E9C60A4A66A64A640E103F08982ED6577087118F0EBC7EB5D0A00004A04000009F3F01980FE00000111590189000161339587000000000000000000||SONIKS: Station_22-KO04hr
2024-03-10 09:50:20|848A82869E9C60A4A66A64A640E103F06882ED659D05DD11F0EBCEEB5D0A00004A0400000BF2F01780FE00000111590189000161339487000000000000000000||SONIKS: Station_22-KO04hr
2024-03-10 09:49:47|848A82869E9C60A4A66A64A640E103F04882ED65A1050C12F0EBC9EB5D0A00004A0400000CF1F01580FD00000111590189000161339387000000000000000000||SONIKS: Station_22-KO04hr
...
```

One image consits of multiple frames, each frame containing just 56 bytes of payload. A full image requires quite a few frames to transmit. Reception is not perfect, some blocks are usually missing, but we have some redundancy in the csv, because multiple people are sending in frames, and Stratosat TK-1 usually transmits the same image 3-4 times in a row. 

This tool tries to combine these, filling out the missing pieces. 

It's not a bullet proof solution though. Frames are ordered by timestamp, then the header of the first image blocks are examined. If it has not changed since the previous image, it's supposed that we are dealing with the same transmission again. 

When using wav mode, gr_satellites` should be in "/usr/bin/gr_satellites". (That's how the dockerfile is built.)
