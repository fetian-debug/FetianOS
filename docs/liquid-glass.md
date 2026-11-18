# FETIANOS Liquid Glass 2090

The current implementation is a compositor-effects baseline: native blur,
shadow, rounding, gradient focus borders, springs and restrained translucent
Waybar panels. Application content remains opaque for readability. Source
configuration has been checked against the pinned release's example and APIs;
GPU output and performance have not been validated.

`desktop/hyprland/airootfs/usr/share/fetian/hyprland/materials.json` defines the six
material families as design tokens. Obsidian is the panel foundation, Plasma
marks focus, Cosmic is the workspace direction, Titanium is the settings
direction, Crystal is the overlay direction, and Pearl is reserved for a future
light theme. The file does not implement a GPU material engine or apply all six
families to existing GTK applications.

| Effect | Status |
|---|---|
| Background blur, shadows, rounded geometry | Configured native Hyprland effects, awaiting GPU verification |
| Gradient border and animated focus transition | Native configuration |
| Translucent status panel/dock | GTK panel styles with a Hyprland layer blur rule |
| Optical refraction, Fresnel reflections, dispersion | Not implemented |
| Dynamic environment/cursor reflections | Not implemented |
| Depth-aware blur, ambient occlusion, bloom | Not implemented |
| Solid/reduced-motion fallback | Performance/accessible compositor profiles and solid panel CSS |

Cinematic increases blur passes and shadow range; balanced uses moderate values.
Neither runs a custom continuous wallpaper animation. Performance and accessible
disable blur/animation and use opaque surfaces. Accessible increases text size
and focus-border contrast. Text contrast, screen readers, scaling and all
monitor sizes still require accessibility testing.

A future native UI shader pipeline should render local surface bounds, cache
resources, suspend idle animation and expose measured quality levels. Do not
present these baseline styles as physically accurate glass or measured 60 FPS.
