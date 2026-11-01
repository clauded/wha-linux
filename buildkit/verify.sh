#!/usr/bin/env bash
set -euo pipefail
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python="$root/out/WiiM-Home-Linux/runtime/venv/bin/python"
[[ -x $python ]] || { echo "Build first with ./bootstrap.sh --dmg ..." >&2; exit 1; }
export QT_QPA_PLATFORM=${QT_QPA_PLATFORM:-offscreen}
export XDG_CACHE_HOME="$root/.test-cache" XDG_CONFIG_HOME="$root/.test-config" XDG_DATA_HOME="$root/.test-data"
export BEETSDIR="$XDG_CONFIG_HOME/beets" PYTHONNOUSERSITE=1
unset PYTHONHOME
export PYTHONPATH="$root/linux" WIIM_QT_BINDING
WIIM_QT_BINDING=$("$python" -c 'import json,sys; print(json.load(open(sys.argv[1]))["qt_binding"])' "$root/out/WiiM-Home-Linux/build-metadata.json")
mkdir -p "$root/.test-cache" "$root/.test-config" "$root/.test-data"
mkdir -p "$BEETSDIR"
trap 'rm -rf "$root/.test-cache" "$root/.test-config" "$root/.test-data"' EXIT
cd "$root/out/WiiM-Home-Linux/app"
for test in tests/test_tidal_home_loading_qml.py tests/test_tidal_collection_item_count_qml.py tests/test_requests_cache_legacy_api.py tests/test_radio_paradise_channel_cache.py tests/test_preset_key_mapping.py tests/test_preset_callback.py tests/test_sound_output_normalization.py tests/test_wiimradio_artwork_fallback.py tests/test_app_icon.py tests/test_single_instance.py tests/test_observer_lifecycle.py tests/test_requests_cache_migration.py; do
  "$python" "$root/$test"
done
"$python" "$root/tests/test_close_behavior.py"
"$python" "$root/tests/test_runtime_options.py"
echo "All automated regressions passed. Real-device acceptance is documented in docs/REPRODUCIBILITY.md."
