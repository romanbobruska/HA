#!/bin/bash
# Wrapper pro zpetnou kompatibilitu se SSH commandem v ZAKONY.TXT 2.1.
# Vlastni logika je v scripts/deploy.sh — vsechny argumenty jsou predany dale.
exec bash "$(dirname "$0")/scripts/deploy.sh" "$@"
