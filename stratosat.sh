#!/bin/bash

docker run --rm -v `pwd`:/data cubesats /app/stratosat.py $@