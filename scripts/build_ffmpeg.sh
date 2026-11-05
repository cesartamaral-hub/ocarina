#!/bin/bash
# Builds the small ffmpeg that goes inside Ocarina.app: the official source, LGPL only (no GPL parts, no other libraries), static, arm64.
# It reads and writes what the app needs (wav, mp3, aac/m4a, ogg/opus/vorbis, flac, mp4/webm audio) and nothing else.
# Output: desktop/vendor/ffmpeg and desktop/vendor/ffmpeg-LICENSE.txt. Run once; desktop/build.sh puts the result in the app.
# Needs Xcode's command line tools. The source is checked against the SHA-256 below.
set -euo pipefail
VERSION=9.0.2
SHA256=8c3850283eb25fa026482078a04051e0be17347b09ef81a0849bec15a96e002e
HERE="$(cd "$(dirname "$0")/.." && pwd)"
WORK="${FFMPEG_WORK:-$HOME/Lute-Ocarina/ffmpeg-build}"
mkdir -p "$WORK" "$HERE/desktop/vendor"
cd "$WORK"
[ -f ffmpeg.tar.xz ] || curl -fsSL -o ffmpeg.tar.xz "https://ffmpeg.org/releases/ffmpeg-$VERSION.tar.xz"
echo "$SHA256  ffmpeg.tar.xz" | shasum -a 256 -c -
rm -rf src && mkdir src && tar -xf ffmpeg.tar.xz -C src --strip-components=1
cd src
./configure --disable-everything --disable-autodetect --disable-doc --disable-ffplay --disable-ffprobe --disable-network \
  --disable-debug --enable-static --disable-shared --arch=arm64 \
  --extra-cflags="-mmacosx-version-min=13.0" --extra-ldflags="-mmacosx-version-min=13.0" \
  --enable-protocol=file,pipe \
  --enable-demuxer=wav,mp3,aac,ogg,flac,mov,matroska,concat \
  --enable-decoder=pcm_s16le,pcm_s24le,pcm_s32le,pcm_f32le,pcm_f64le,pcm_u8,mp3,mp3float,aac,aac_latm,vorbis,opus,flac,alac \
  --enable-muxer=wav,mp4,ipod,ogg,adts,pcm_s16le,pcm_f32le,null --enable-encoder=pcm_s16le,pcm_s24le,pcm_f32le,aac,flac \
  --enable-parser=aac,aac_latm,mpegaudio,vorbis,opus,flac --enable-bsf=aac_adtstoasc \
  --enable-filter=aresample,aformat,anull,atrim,asetpts,volume,atempo,amix,pan,adelay,apad
make -j"$(sysctl -n hw.ncpu)"
cp ffmpeg "$HERE/desktop/vendor/ffmpeg"
cp COPYING.LGPLv2.1 "$HERE/desktop/vendor/ffmpeg-LICENSE.txt"
strip "$HERE/desktop/vendor/ffmpeg"
"$HERE/desktop/vendor/ffmpeg" -hide_banner -version | head -2
