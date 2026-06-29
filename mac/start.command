#!/bin/zsh
cd "$(dirname "$0")"

APP="./bin/LibertyPet"
SOURCE="./src/LibertyPet.swift"

if [[ ! -x "$APP" || "$SOURCE" -nt "$APP" ]]; then
  mkdir -p ./bin
  mkdir -p ./.build/module-cache
  /usr/bin/xcrun swiftc -module-cache-path ./.build/module-cache "$SOURCE" -o "$APP" -framework AppKit
  if [[ $? -ne 0 ]]; then
    osascript -e 'display dialog "LibertyPet のビルドに失敗しました。" buttons {"OK"} default button "OK"'
    exit 1
  fi
fi

"$APP"
