#!/bin/bash

SDE_URL="https://www.fuzzwork.co.uk/dump/sqlite-latest.sqlite.bz2"

echo "Downloading SDE from ${SDE_URL}"
curl -o sde.sqlite.bz2 "${SDE_URL}" && bunzip2 -f sde.sqlite.bz2
if [ -e sde.sqlite ]; then
    echo "Generating reference data"
    /usr/bin/env python gen_reference_data.py sde.sqlite
    cp *.json dropbot/data/
    
    echo "Running unit tests"
    /usr/bin/env python setup.py test > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        git status
        echo "SDE data updated successfully"
    else
        echo "Unit tests failed, please investigate"
    fi
else
    echo "Error downloading SDE"
    exit 1
fi
