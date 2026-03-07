#!/bin/bash
# Force wheel-only installation to avoid compilation
pip install --only-binary :all: -r requirements.txt
