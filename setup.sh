#!/bin/bash
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created"
fi

source venv/bin/activate

pip install -r Requirements.txt

echo "Dependencies installed"
