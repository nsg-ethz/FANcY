#!/usr/bin/env bash

# fancy dir
FANCY_DIR="/home/fancy/fancy"

# create fancy dir if it does not exist
mkdir -p ${FANCY_DIR}

./base-dependencies.sh

# installs all dependencies 
./ns3-dependencies.sh

# switch to ns3 path
NS3_PATH="/home/fancy/fancy/fancy-code/simulation/"

cd ${NS3_PATH}
# build ns3
./waf clean
CXXFLAGS="-Wall -g -O0" ./waf configure --enable-tests --build-profile=debug --enable-examples --python=/usr/local/bin/python3
./waf build

