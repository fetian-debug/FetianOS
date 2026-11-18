# FetianFiles preview

No FetianFiles implementation existed in the inspected source tree. The preview
uses Python/GTK4/GIO, matching the existing desktop applications. System metrics
and privileged system boundaries remain in the existing Rust components; no Rust
service or security restriction was removed. No additional GUI framework or
third-party Python package was introduced.

Run from the source tree as a regular Linux desktop user:

```bash
python3 apps/fetian-files/fetian_files.py "$HOME"
python3 apps/fetian-files/fetian_files.py --rtl "$HOME"
```

Both image profiles stage `/usr/bin/fetian-files` and a hidden desktop entry.
Thunar remains the primary. The preview is not started at login and never runs
as root. `fileops.py`, `archiveops.py`, `preferences.py` and `image_preview.py`
separate local mutation, archive handling, preferences and raster decoding from
GTK/GIO presentation.

Implemented:

- Home/XDG folders, custom locations, breadcrumbs, back/up, bookmarks, recent,
  Trash, network and volume sidebars; asynchronous GIO enumeration.
- List/grid/compact views, tabs and local tab restoration, independent split
  panes, multi-selection, context actions and keyboard navigation.
- Local copy/move/create/rename, batch rename patterns, owner permission editing,
  explicit permanent deletion, GIO Trash/restore and single-move undo.
- Native URI clipboard and copy drag/drop. Drag/drop never implicitly moves data;
  explicit cut/paste handles moves. Local and GIO-backed transfers report errors.
- Bounded recursive filename search with file/folder, size and modification-date
  filters; no background index or indexing daemon.
- Read-only text preview up to 128 KiB, properties and resource-limited PNG/JPEG/
  GIF/WebP thumbnails. Previews never launch the selected file.
- Integrated archive listing, extraction into fresh folders, selected-file
  extraction and ZIP creation with compression levels 0–9. ZIP, TAR, compressed
  TAR, standalone GZIP and XZ are supported. Unknown stream sizes are labeled.
- Safe GIO mount/unmount/eject requests and authentication-capable mount operations;
  no forced unmount or privileged custom storage helper.
- System/light/dark appearance, inherited GTK accent, focus outlines, labeled
  controls, optional preview, reduced motion, and RTL layout with English text.

Safety boundaries:

Local operations walk directory descriptors with `O_NOFOLLOW`; atomic
`renameat2(RENAME_NOREPLACE)` prevents clobbering existing destinations. Copies
commit private temporary output only after success. Links are copied as links;
devices, FIFOs and sockets are rejected. Cross-device directory/link moves are
refused; regular-file moves retain the source if verification detects changes.
No filesystem operation is elevated. Permission editing is local, nonrecursive,
and excludes special mode bits; unreadable owned files may still require a
terminal to restore access. Directory copies retain owner access for usability
and safe cleanup rather than exactly reproducing restrictive source modes.

Cancellation leaves completed operations intact. Multi-item jobs may partially
complete; permanent deletion is irreversible and may partially complete. Batch
rename attempts identity-checked rollback and reports any incomplete rollback.
Undo covers one successful move/rename, not deletion, Trash history or arbitrary
transactions. These protections reduce races; they do not make all concurrent
filesystem mutations race-proof or provide power-loss transactions.

Archives never call `extractall`. Absolute/traversing/Windows paths, links,
hardlinks, special files, sparse entries, conflicts and excessive expansion are
rejected. Worker limits: 512 MiB address space, 30 CPU seconds, 40-second GUI
deadline; input 256 MiB, member 256 MiB, total output 1 GiB, 10,000 entries.
ZIP central-directory parsing is also subject to process limits. Abrupt worker
termination can leave a hidden `.fetian-job-*` directory for manual inspection;
no existing destination is overwritten. Archive listing displays up to 1,000
rows, while extraction retains its independent limits.

Raster decoding runs in a separate worker with 256 MiB address space, 5 CPU
seconds and a 10-second caller deadline; input is limited to 16 MiB and 16 million
pixels, output to 384 pixels per side. SVG and other formats use the external
viewer. This is resource isolation, not a filesystem/network sandbox or a claim
that native decoder vulnerabilities are impossible. Current GUI job cancellation
may wait for that bounded image deadline.

GIO Trash has no permanent-delete fallback. Restoration refuses overwrites.
Embedded URL passwords are rejected; bookmark persistence omits URL passwords,
queries and fragments. Only local tabs are automatically restored. Remote
authentication credentials are not stored in the app's preferences.

Still incomplete / unverified:

- 7z, encrypted archives, TAR/7z creation and full archive editing.
- PDF/audio/video previews, metadata-content search and thumbnail caching.
- Recursive remote copy; backend capability failures are surfaced. No proprietary
  SMB/MTP stack is implemented.
- Authenticated SMB browsing, real MTP transfers, hot unplug, USB eject and busy
  filesystem behavior on target hardware. Eject is requested only when the GIO
  mount advertises support; it is not forced and has not been hardware-tested.
- Full Arabic translation, screen-reader acceptance, touch/scaling and large-
  directory performance profiling. Enumeration stops at 20,000 items; recursive
  search stops at 50,000 examined / 2,000 results. Use Thunar for larger locations.
- Clipboard protocol differences across non-GTK file managers, real pointer
  drag/drop interaction, compositor integration and installed-image acceptance.

Tests use disposable data. The headless GTK smoke test actually exercises native
clipboard deserialization, GIO local Trash/restore, text/Arabic and raster
previews, tabs, split view, search and appearance controls. Device/disconnect
checks use fake providers, not phones or drives. See [test evidence](verification-2026-11-18.md).
