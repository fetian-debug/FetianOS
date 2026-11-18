-- Moderate compositor effects; opaque application content preserves readability.
hl.config({ animations = { enabled = true }, decoration = {
    blur = { enabled = true, size = 5, passes = 2 },
    shadow = { enabled = true, range = 16 },
} })
