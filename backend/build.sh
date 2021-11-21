#!/bin/sh
docker run -it --rm -v "$(pwd)":"$(pwd)" -w "$(pwd)" maven:alpine mvn clean package