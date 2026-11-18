-- FETIANOS 2090. API target: Hyprland v0.56.2, not rolling git.
local root = "/usr/share/fetian/hyprland/"
local profile = "balanced"
local config_home = os.getenv("XDG_CONFIG_HOME") or ((os.getenv("HOME") or "") .. "/.config")
local file = io.open(config_home .. "/fetian/effects", "r")
if file then profile = file:read("*l") or profile; file:close() end
local allowed = { balanced = true, cinematic = true, performance = true, accessible = true }
if not allowed[profile] then profile = "balanced" end

hl.monitor({ output = "", mode = "preferred", position = "auto", scale = "auto" })
hl.env("XCURSOR_SIZE", "24")
hl.config({
    general = {
        gaps_in = 6, gaps_out = 16, border_size = 2, layout = "dwindle",
        resize_on_border = true, allow_tearing = false,
        col = {
            active_border = { colors = { "rgba(76e4ffff)", "rgba(b49bffff)" }, angle = 35 },
            inactive_border = "rgba(414958ff)",
        },
    },
    decoration = {
        rounding = 16, rounding_power = 2,
        active_opacity = 1.0, inactive_opacity = 1.0,
        blur = { enabled = true, size = 5, passes = 2, vibrancy = 0.12 },
        shadow = { enabled = true, range = 16, render_power = 3, color = 0x66080c18 },
    },
    animations = { enabled = true },
    input = { kb_layout = "us,ara", kb_options = "grp:alt_shift_toggle", follow_mouse = 1 },
    dwindle = { preserve_split = true },
    misc = { disable_hyprland_logo = true, force_default_wallpaper = 0 },
})
hl.curve("fetian-settle", { type = "spring", mass = 1, stiffness = 220, dampening = 25 })
hl.curve("fetian-soft", { type = "bezier", points = { {0.2, 0.8}, {0.2, 1} } })
hl.animation({ leaf = "windows", enabled = true, speed = 4, spring = "fetian-settle" })
hl.animation({ leaf = "workspaces", enabled = true, speed = 3, bezier = "fetian-soft", style = "slide" })
hl.animation({ leaf = "border", enabled = true, speed = 4, bezier = "fetian-soft" })
dofile(root .. "profiles/" .. profile .. ".lua")
hl.layer_rule({ name = "fetian-panel-blur", match = { namespace = "waybar" },
    blur = profile == "balanced" or profile == "cinematic" })

local function launch(key, command) hl.bind(key, hl.dsp.exec_cmd(command)) end
launch("SUPER + Return", "foot")
launch("SUPER + D", "wofi --show drun --allow-images")
launch("SUPER + space", "wofi --show drun --allow-images")
launch("SUPER + comma", "fetian-control-center")
launch("SUPER + SHIFT + A", "fetian-apps")
launch("SUPER + E", "thunar")
launch("SUPER + Tab", "fetian-desktop workspaces")
launch("SUPER + I", "fetian-desktop monitor")
launch("SUPER + L", "systemctl --user start fetian-lock.service")
launch("SUPER + SHIFT + E", "fetian-desktop power")
launch("SUPER + SHIFT + C", "hyprctl reload")
launch("Print", "fetian-screenshot region")
launch("SUPER + Print", "fetian-screenshot screen")
hl.bind("SUPER + SHIFT + Q", hl.dsp.window.close())
hl.bind("SUPER + V", hl.dsp.window.float({ action = "toggle" }))
hl.bind("SUPER + F", hl.dsp.window.fullscreen())
for _, direction in ipairs({ "left", "right", "up", "down" }) do
    hl.bind("SUPER + " .. direction, hl.dsp.focus({ direction = direction }))
end
for workspace = 1, 10 do
    local key = workspace % 10
    hl.bind("SUPER + " .. key, hl.dsp.focus({ workspace = workspace }))
    hl.bind("SUPER + SHIFT + " .. key, hl.dsp.window.move({ workspace = workspace }))
end
hl.bind("SUPER + mouse:272", hl.dsp.window.drag(), { mouse = true })
hl.bind("SUPER + mouse:273", hl.dsp.window.resize(), { mouse = true })
hl.gesture({ fingers = 3, direction = "horizontal", action = "workspace" })
for key, command in pairs({
    XF86AudioRaiseVolume = "wpctl set-volume -l 1 @DEFAULT_AUDIO_SINK@ 5%+",
    XF86AudioLowerVolume = "wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-",
    XF86AudioMute = "wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle",
    XF86MonBrightnessUp = "brightnessctl set 5%+",
    XF86MonBrightnessDown = "brightnessctl set 5%-",
}) do launch(key, command) end
hl.window_rule({ name = "fetian-control-center", match = { class = "online.fetian.ControlCenter" }, float = true })
hl.window_rule({ name = "fetian-navigation", match = { class = "online.fetian.Desktop" }, float = true })
hl.window_rule({ name = "fetian-audio", match = { class = "org.pulseaudio.pavucontrol" }, float = true })
hl.on("hyprland.start", function() hl.exec_cmd("fetian-session-ready") end)
