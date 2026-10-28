#!/bin/bash
set -euo pipefail
python3 /home/deploy/obfuscator-control/scripts/cutover-backends.py apply
