"use strict";
(async () => {
  const root = document.getElementById("releases");
  const element = (tag, text, className) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  };
  try {
    const configURL = new URL("assets/repository.json", document.baseURI);
    const configResponse = await fetch(configURL);
    if (!configResponse.ok) throw new Error("Repository configuration unavailable");
    const { repository } = await configResponse.json();
    if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repository)) throw new Error("Invalid repository");
    const response = await fetch(`https://api.github.com/repos/${repository}/releases?per_page=20`, {
      headers: { Accept: "application/vnd.github+json" }
    });
    if (!response.ok) throw new Error(`GitHub returned ${response.status}`);
    const releases = await response.json();
    if (!Array.isArray(releases)) throw new Error("Invalid release response");
    const published = releases.filter(release => !release.draft && release.published_at && Array.isArray(release.assets)
      && release.assets.some(asset => /^(sway|hyprland)-downloads\.json$/.test(asset.name)))
      .sort((a, b) => new Date(b.published_at) - new Date(a.published_at)).slice(0, 5);
    root.replaceChildren();
    if (!published.length) root.append(element("p", "No ISO preview has been published yet. Check the build runs or build from source."));
    for (const release of published) {
      const card = element("article", undefined, "release");
      card.append(element("h2", release.name || release.tag_name));
      card.append(element("p", `${release.tag_name} · ${new Date(release.published_at).toLocaleDateString()} · developer preview`, "meta"));
      const list = element("ul");
      for (const asset of release.assets) {
        const url = new URL(asset.browser_download_url);
        if (url.protocol !== "https:" || url.hostname !== "github.com" || !url.pathname.startsWith(`/${repository}/releases/download/`)) continue;
        const item = element("li");
        const link = element("a", asset.name); link.href = url.href;
        item.append(link, document.createTextNode(` · ${(asset.size / 1024 ** 2).toFixed(1)} MiB`));
        list.append(item);
      }
      card.append(list);
      const details = element("a", "Release notes and test status ↗");
      details.href = `https://github.com/${repository}/releases/tag/${encodeURIComponent(release.tag_name)}`;
      card.append(details); root.append(card);
    }
  } catch (error) {
    root.replaceChildren(element("p", "Could not load the release list. Open GitHub Releases below to check published downloads."));
    console.warn("Release list unavailable:", error.message);
  }
})();
