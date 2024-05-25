#!/bin/bash

docker run --rm -v `pwd`:/data geoscan /app/stratosat.py $@