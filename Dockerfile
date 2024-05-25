
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive


RUN apt-get update --fix-missing \
    && apt install -y software-properties-common \
    && apt install -y git \
    && rm -rf /var/lib/apt/lists/* \
    && add-apt-repository ppa:daniestevez/gr-satellites \
    && apt install -y gr-satellites \
    && rm -rf /var/lib/apt/lists/* \
    && apt clean

COPY *.py /app/

WORKDIR /data
ENTRYPOINT ["/usr/bin/python3"]