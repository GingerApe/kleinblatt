#!/bin/bash

# Set variables
KB_Logistik="KB_Logistik"
DMG_NAME="${KB_Logistik}.dmg"
TMP_DMG="tmp_dmg"
DIST_PATH="dist"

# Clean up any previous files
rm -rf "$TMP_DMG" "$DMG_NAME"
mkdir "$TMP_DMG"

# Copy the app to the temporary directory
cp -r "${DIST_PATH}/${KB_Logistik}" "$TMP_DMG"

# Create a symbolic link to Applications
ln -s /Applications "$TMP_DMG"

# Create the DMG
hdiutil create -volname "$KB_Logistik" -srcfolder "$TMP_DMG" -ov -format UDZO "$DMG_NAME"

# Clean up
rm -rf "$TMP_DMG"

echo "DMG created successfully: $DMG_NAME"