#!/usr/bin/env bash
set -euo pipefail
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source_dmg=${WIIM_OFFICIAL_DMG:?Run ./bootstrap.sh --dmg /path/to/official.dmg}
command -v uv >/dev/null || { echo "Missing uv: install it from https://docs.astral.sh/uv/" >&2; exit 1; }
export RCC="${RCC:-rcc}"
command -v "$RCC" >/dev/null || { echo "Missing rcc. On Arch/Manjaro: sudo pacman -S qt6-base" >&2; exit 1; }
work="$root/work"
out="$root/out/WiiM-Home-Linux"
rm -rf "$work" "$out" "$root/dist"
mkdir -p "$work" "$root/out"
python3 "$root/tools/extract_installer.py" "$source_dmg" "$work/extracted"
binary=$(find "$work/extracted" -path '*WiiM Home.app/Contents/MacOS/WiiM Home' -type f -print -quit)
resources=$(dirname "$(dirname "$binary")")/Resources
[[ -n $binary && -d $resources ]] || { echo "Invalid extracted official application" >&2; exit 1; }
export UV_CACHE_DIR="${UV_CACHE_DIR:-$root/.uv-cache}"
UV_PYTHON_INSTALL_DIR="$work/python" UV_PYTHON_BIN_DIR="$work/bin" uv python install 3.9.25
py39=$(find "$work/python" -type f -path '*/bin/python3.9' -print -quit)
[[ -n $py39 ]] || { echo "uv did not install Python 3.9" >&2; exit 1; }
uv run --python "$py39" --with pyinstaller==6.22.3 python "$root/tools/unpack_pyz.py" "$binary" "$work/pyz"
"$py39" "$root/tools/inspect_source.py" "$(dirname "$resources")" "$work"
export WIIM_QT_BINDING
WIIM_QT_BINDING=$("$py39" -c 'import json,sys; print(json.load(open(sys.argv[1]))["qt_binding"])' "$work/source-metadata.json")
uv venv --python "$py39" "$out/runtime/venv"
requirements="$root/requirements-pyqt6.lock"
if [[ $WIIM_QT_BINDING == PySide6 ]]; then requirements="$root/requirements-pyside6.lock"; fi
uv pip install --python "$out/runtime/venv/bin/python" -r "$requirements"
mkdir -p "$out/app" "$out/resources"
cp -a "$work/pyz/." "$out/app/"
cp -a "$resources/data" "$out/app/"
# LPUtility resolves shared configuration relative to the HOME package while
# other code resolves the same official resource from app/data.
mkdir -p "$out/app/HOME"
cp -a "$resources/data" "$out/app/HOME/"
if [[ -d "$resources/Qml" ]]; then cp -a "$resources/Qml" "$out/app/"; fi
cp -a "$resources/images" "$out/app/"
export PYTHONPATH="$root/linux"
"$out/runtime/venv/bin/python" "$root/tools/materialize_resources.py" "$out/app"
python3 "$root/tools/patch_qml.py" "$out/app" "$root/patches/qml-transforms.json"
"$out/runtime/venv/bin/python" "$root/tools/rebuild_qt_resources.py" "$out/app"
"$out/runtime/venv/bin/python" "$root/tools/verify_qrc.py" "$out/app"
cp -a "$out/app/Qml" "$out/resources/"
cp -a "$resources/images" "$out/resources/"
cp "$root/linux/bootstrap.py" "$root/linux/runtime_options.py" "$root/linux/preset_fix.py" "$root/linux/sound_output_fix.py" "$root/linux/single_instance.py" "$root/linux/observer_lifecycle_fix.py" "$root/linux/cache_compat.py" "$root/linux/wiimradio_artwork_fallback.py" "$root/linux/app_icon.py" "$out/"
cp -a "$root/linux/qt_compat" "$out/"
cp "$work/source-metadata.json" "$out/build-metadata.json"
mkdir -p "$out/app/LPClientFramework/util"
cp "$root/linux/LPClientFramework/util/LPNativeCrashHandler.py" "$out/app/LPClientFramework/util/"
ln -s out "$root/dist"
cat > "$out/run.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export PYTHONPATH="$base/runtime/venv/lib/python3.9/site-packages:$base/app"
export WIIM_HOME_RESOURCES="$base/resources" WIIM_HOME_APP="$base/app"
export WIIM_QT_BINDING
WIIM_QT_BINDING=$("$base/runtime/venv/bin/python" -c 'import json,sys; print(json.load(open(sys.argv[1]))["qt_binding"])' "$base/build-metadata.json")
export XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}" XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}" XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
export BEETSDIR="${BEETSDIR:-$XDG_CONFIG_HOME/beets}"
mkdir -p "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" "$BEETSDIR"
cd "$base/app"; exec "$base/runtime/venv/bin/python" "$base/bootstrap.py" "$@"
EOF
chmod +x "$out/run.sh"
echo "Built $out"
