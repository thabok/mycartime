#!/bin/sh
export NODE_OPTIONS=--openssl-legacy-provider
cd frontend
npm install --silent
npm install react-scripts@latest -g --silent
npm start
