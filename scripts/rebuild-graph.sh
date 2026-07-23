#!/bin/bash

echo "Rebuilding graph..."

python -m graphify . --deep

echo "Done"