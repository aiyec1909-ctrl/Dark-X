[app]

title = Dark-X
package.name = darkx
package.domain = org.darkx

source.dir = .
source.include_exts = py,png,jpg,jpeg,gif,wav,mp3,ttf,txt

version = 1.0

requirements = python3,pygame

orientation = landscape
fullscreen = 1

android.minapi = 21
android.archs = arm64-v8a,armeabi-v7a

android.permissions = INTERNET,VIBRATE

log_level = 2

[buildozer]

warn_on_root = 1
