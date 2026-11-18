"""Lua syntax/profile evaluation only; this does not validate a compositor or GPU."""
import ctypes
import ctypes.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "desktop/hyprland/airootfs/usr/share/fetian/hyprland"
LIBRARY = next((value for name in ("lua5.4", "lua5.3", "lua5.1", "lua")
                if (value := ctypes.util.find_library(name))), None)


@unittest.skipUnless(LIBRARY, "Lua library needed for syntax/profile evaluation")
class LuaConfigTests(unittest.TestCase):
    def evaluate(self, source):
        lua = ctypes.CDLL(LIBRARY)
        lua.luaL_newstate.restype = ctypes.c_void_p
        lua.luaL_openlibs.argtypes = [ctypes.c_void_p]
        lua.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        lua.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
        lua.lua_tolstring.restype = ctypes.c_char_p
        lua.lua_close.argtypes = [ctypes.c_void_p]
        state = lua.luaL_newstate()
        try:
            lua.luaL_openlibs(state)
            status = lua.luaL_loadstring(state, source.encode())
            if status == 0:
                if hasattr(lua, "lua_pcall"):
                    lua.lua_pcall.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
                    status = lua.lua_pcall(state, 0, 0, 0)
                else:
                    lua.lua_pcallk.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ssize_t, ctypes.c_void_p]
                    status = lua.lua_pcallk(state, 0, 0, 0, 0, None)
            error = lua.lua_tolstring(state, -1, None) if status else b""
            self.assertEqual(status, 0, error.decode() if error else "Lua error")
        finally:
            lua.lua_close(state)

    def test_all_profiles_evaluate_and_reduced_effects_stay_disabled(self):
        # Minimal public-API stubs exercise our composition and option overrides;
        # actual option acceptance still requires the pinned Hyprland executable.
        harness = '''
local state = {}
local function merge(a,b)
  for k,v in pairs(b) do
    if type(v)=="table" then a[k]=a[k] or {}; merge(a[k],v) else a[k]=v end
  end
end
local function noop(...) return function() end end
hl = { config=function(v) merge(state,v) end, monitor=noop, env=noop,
  curve=noop, animation=noop, bind=noop, gesture=noop, window_rule=noop,
  layer_rule=noop, on=noop,
  dsp={exec_cmd=noop, focus=noop, window={close=noop,float=noop,fullscreen=noop,move=noop,drag=noop,resize=noop}} }
'''
        original = (ASSETS / "hyprland.lua").read_text()
        for profile in ("balanced", "cinematic", "performance", "accessible"):
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as directory:
                home = Path(directory)
                (home / "fetian").mkdir()
                (home / "fetian/effects").write_text(profile + "\n")
                setup = f'local realgetenv=os.getenv; os.getenv=function(k) if k=="XDG_CONFIG_HOME" then return {json.dumps(str(home))} else return realgetenv(k) end end\n'
                source = original.replace('"/usr/share/fetian/hyprland/"', json.dumps(str(ASSETS) + "/"))
                enabled = "true" if profile in ("balanced", "cinematic") else "false"
                checks = f'\nassert(state.animations.enabled=={enabled}); assert(state.decoration.blur.enabled=={enabled}); assert(state.decoration.active_opacity==1.0)\n'
                self.evaluate(harness + setup + source + checks)


if __name__ == "__main__":
    unittest.main()
