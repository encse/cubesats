#!/bin/bash

docker run --rm -v `pwd`:/data cubesats /usr/bin/gr_satellites $@