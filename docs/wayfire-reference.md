# Wayfire reference and spatial roadmap

[Wayfire](https://github.com/WayfireWM/wayfire) is a reference for workspace depth
and spatial navigation. No Wayfire code or plugin is loaded into Hyprland, and
the image does not run a second compositor. Its MIT license notice is preserved
under `licenses/`; Hyprland retains its separate BSD-3-Clause license.

| Experience | Initial implementation / decision |
|---|---|
| Spatial navigation | Native workspace transitions, gestures and keyboard focus/move bindings |
| Multi-monitor organization | Native monitor discovery plus IPC workspace/window text navigator |
| Elastic window transitions | Native spring configuration, subject to compositor testing |
| Workspace previews | Not implemented; text list is labeled honestly |
| Drag/drop organization | Not implemented; use native keyboard move bindings |
| Workspace groups/naming UI | Not implemented; navigator displays existing compositor names |
| Cube / perspective overview | Requires compositor rendering or a compatible audited plugin; deferred |
| Wobbly movement | Not enabled in the 0.56.2 candidate; assess newer upstream support after a package migration |
| Depth-aware floating geometry | No true 3D/window-depth pipeline implemented |

These are feasibility boundaries, not claims that a window-list animation is a
3D compositor effect. An optional overview must use a supported capture protocol
with privacy controls, avoid copying private compositor internals and preserve
keyboard navigation and reduced-motion behavior. No fork is justified for the
current integration milestone.
