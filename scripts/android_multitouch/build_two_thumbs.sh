#!/usr/bin/env bash
# Builds TwoThumbs into a dex file for app_process (no Android SDK platform jar needed).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
work="$(mktemp -d)"
r8_jar="${R8_JAR:?set R8_JAR to an r8 jar, e.g. r8-9.6.0-alpha02.jar}"
javac --release 8 -Xlint:-options -d "$work/classes" "$here/TwoThumbs.java"
java -cp "$r8_jar" com.android.tools.r8.D8 --min-api 30 --output "$work/dex" $(find "$work/classes" -name '*.class')
cp "$work/dex/classes.dex" "${1:-$here/TwoThumbs.dex}"
rm -rf "$work"
echo "built ${1:-$here/TwoThumbs.dex}"
