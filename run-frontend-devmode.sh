#!/bin/sh
docker run --rm -v "$(pwd)":"$(pwd)" -w "$(pwd)" -p 3000:3000 node:alpine ./frontend/run_dev_mode.sh