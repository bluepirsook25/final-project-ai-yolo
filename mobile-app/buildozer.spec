[app]
title = LuxeSmile Dental
package.name = luxesmiledental
package.domain = org.dental
version = 1.0
source.dir = .
source.include_exts = py,png,jpg,jpeg,json
requirements = python3,kivy,android,pillow
orientation = portrait
fullscreen = 0

android.minapi = 26
android.api = 36
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.permissions = INTERNET,CAMERA,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

[buildozer]
log_level = 2
warn_on_root = 1
