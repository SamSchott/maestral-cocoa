#!/usr/bin/env bash

set -e

if [ -z "$1" ]; then
    echo "Specify bundle path as first parameter"
    exit 1
fi
BUNDLE_PATH="$1"

echo "# ==== copy over CLI executable ================================================="

cp "bin/maestral-cli" "$BUNDLE_PATH/Contents/MacOS/maestral-cli"
chmod +x "$BUNDLE_PATH/Contents/MacOS/maestral-cli"

echo "# ==== copy over entry-points metadata required by maestral ====================="

python3 -m pip install --upgrade --no-deps . --target dist 1> /dev/null
DIST_INFO_PATH=$( find dist -name "maestral_cocoa-*.dist-info" )
DIST_INFO_TARGET_PATH=$( find "$BUNDLE_PATH/Contents/Resources/app/" -name "maestral_cocoa-*.dist-info" )
cp "$DIST_INFO_PATH/entry_points.txt" "$DIST_INFO_TARGET_PATH/entry_points.txt"
rm -Rf dist

echo "# ==== prune py files and replace with pyc ======================================"

# compile all py files
"$BUNDLE_PATH/Contents/MacOS/Maestral" --run-python -OO -m compileall -b -d "" "$BUNDLE_PATH" 1> /dev/null

# remove all py files
find "$BUNDLE_PATH/Contents" -name "*.py" ! -name "nslog.py" -delete

# remove all __pycache__ dirs
find "$BUNDLE_PATH/Contents" -name "__pycache__" -prune -exec rm -rf {} \;

echo "# ==== add custom Info.plist entries ============================================"

PLIST_PATH="$BUNDLE_PATH/Contents/Info.plist"

/usr/libexec/PlistBuddy -c "Add :LSUIElement string 1" "$PLIST_PATH"
/usr/libexec/PlistBuddy -c "Set :LSMinimumSystemVersion 10.14.0" "$PLIST_PATH"
/usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier com.samschott.maestral" "$PLIST_PATH"
/usr/libexec/PlistBuddy -c "Add :NSHumanReadableCopyright string 'Copyright © 2020 Sam Schott. All rights reserved.'" "$PLIST_PATH"
