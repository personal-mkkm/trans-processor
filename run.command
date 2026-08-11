#!/bin/bash
# ============================================================
#  Deduction list  ->  Westpac Deskbank CSV payment file
#  Double-click this file to run (Mac). No typing needed.
# ============================================================
cd "$(dirname "$0")"
export PYTHONPATH="$(dirname "$0")/src"

python3 -m trans_processor.cli --input input --output output
status=$?
if [ $status -ne 0 ]; then
    echo
    echo "*** Something needs fixing. Read the ERROR line above,"
    echo "*** correct the spreadsheet in the 'input' folder,"
    echo "*** then double-click run.command again."
fi

echo
echo "Done. Press Enter to close this window."
read _
