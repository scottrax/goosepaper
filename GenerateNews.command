#!/bin/bash
cd "$(dirname "$0")"

OUTFILE="DailyNews-$(date +%Y-%m-%d).pdf"

echo "Generating Daily News PDF: ${OUTFILE}"

docker run --rm --platform linux/amd64 \
    -e OUTPUT_PDF="$OUTFILE" \
    -v "$(pwd)":/goosepaper/mount \
    j6k4m8/goosepaper \
    bash -c '
        # Copy custom providers into the Python path
        cp -r /goosepaper/mount/providers /goosepaper/providers
        # Patch util.py to register custom providers
        cp /goosepaper/mount/providers/util_patch.py /goosepaper/goosepaper/util.py
        # Patch goosepaper.py for TOC header and section anchors
        cp /goosepaper/mount/providers/goosepaper_patch.py /goosepaper/goosepaper/goosepaper.py
        # Copy custom styles into the styles directory
        cp -r /goosepaper/mount/styles/* /goosepaper/styles/
        # Run goosepaper
        goosepaper -c mount/config.json -o "mount/${OUTPUT_PDF}"
    '

if [ $? -eq 0 ]; then
    echo "Done! ${OUTFILE} created."
else
    echo "Error generating PDF. Press any key to close."
    read -n 1
    exit 1
fi

osascript -e 'tell application "Terminal" to close front window' &
