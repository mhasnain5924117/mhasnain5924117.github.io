(() => {
  const yearNodes = document.querySelectorAll("[data-year]");
  yearNodes.forEach((node) => {
    node.textContent = String(new Date().getFullYear());
  });

  const toggle = document.querySelector("[data-menu-toggle]");
  const nav = document.getElementById("site-nav");

  if (toggle && nav) {
    const closeMenu = () => {
      nav.dataset.open = "false";
      toggle.setAttribute("aria-expanded", "false");
    };
    const openMenu = () => {
      nav.dataset.open = "true";
      toggle.setAttribute("aria-expanded", "true");
    };

    toggle.addEventListener("click", () => {
      const isOpen = nav.dataset.open === "true";
      if (isOpen) closeMenu();
      else openMenu();
    });

    document.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof Node)) return;
      if (!nav.contains(target) && !toggle.contains(target)) closeMenu();
    });

    nav.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => closeMenu());
    });

    window.addEventListener("resize", () => {
      if (window.innerWidth > 760) {
        nav.dataset.open = "";
        toggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  initSectionSpy();
  initEducationStepper();
  initPublicationExplorer();
  initMilestones();
})();

function initSectionSpy() {
  const links = Array.from(document.querySelectorAll('.site-nav a[href^="#"]'));
  if (!links.length) return;

  const sections = links
    .map((link) => link.getAttribute("href"))
    .filter((href) => href && href.startsWith("#"))
    .map((href) => document.getElementById(href.replace("#", "")))
    .filter((section) => section instanceof HTMLElement);

  if (!sections.length) return;

  const linkById = new Map();
  links.forEach((link) => {
    const href = link.getAttribute("href");
    if (!href) return;
    linkById.set(href.replace("#", ""), link);
  });

  const setActive = (id) => {
    links.forEach((link) => link.classList.remove("is-active"));
    const activeLink = linkById.get(id);
    if (activeLink) activeLink.classList.add("is-active");
  };

  const observer = new IntersectionObserver(
    (entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
      if (visible.length > 0) setActive(visible[0].target.id);
    },
    { rootMargin: "-40% 0px -45% 0px", threshold: [0.2, 0.4, 0.6] }
  );

  sections.forEach((section) => observer.observe(section));
}

async function initPublicationExplorer() {
  const container = document.getElementById("publication-list");
  if (!container) return;

  const searchInput = document.getElementById("pub-search");
  const filterButtons = Array.from(document.querySelectorAll("[data-pub-filter]"));
  let filterValue = "all";
  let searchValue = "";

  try {
    const items = await loadItems("assets/data/publications.json", "__PUBLICATIONS__");
    if (!Array.isArray(items)) throw new Error("Invalid publication data");

    const render = () => {
      const filtered = items
        .filter((item) => {
          if (filterValue === "all") return true;
          return item.type === filterValue;
        })
        .filter((item) => {
          if (!searchValue) return true;
          const haystack = `${item.title} ${item.authors} ${item.venue} ${item.notes}`.toLowerCase();
          return haystack.includes(searchValue);
        })
        .sort((a, b) => b.year - a.year);

      if (!filtered.length) {
        container.innerHTML = '<p class="mono-note">No publications match the selected filter/search.</p>';
        return;
      }

      container.innerHTML = filtered
        .map((item) => {
          const paperLink = item.paper_url
            ? `<a href="${item.paper_url}" target="_blank" rel="noopener">Paper link</a>`
            : '<span class="mono-note">Paper link to be added</span>';
          return `
            <article class="pub-card">
              <h3>${escapeHtml(item.title)}</h3>
              <p>${escapeHtml(item.authors)}</p>
              <div class="pub-meta">
                <div><span class="label">Year</span><span>${item.year}</span></div>
                <div><span class="label">Type</span><span>${escapeHtml(item.type)}</span></div>
                <div><span class="label">Venue</span><span><a href="${item.venue_url}" target="_blank" rel="noopener">${escapeHtml(item.venue)}</a></span></div>
                <div><span class="label">Impact factor</span><span>${escapeHtml(item.impact_factor)}</span></div>
              </div>
              <p>${escapeHtml(item.notes)}</p>
              <div class="card-actions">${paperLink}</div>
            </article>
          `;
        })
        .join("");
    };

    filterButtons.forEach((button) => {
      button.addEventListener("click", () => {
        filterButtons.forEach((btn) => btn.classList.remove("is-active"));
        button.classList.add("is-active");
        filterValue = button.dataset.pubFilter || "all";
        render();
      });
    });

    if (searchInput) {
      searchInput.addEventListener("input", () => {
        searchValue = searchInput.value.trim().toLowerCase();
        render();
      });
    }

    render();
  } catch (error) {
    container.innerHTML = '<p class="mono-note">Unable to load publication data at this moment.</p>';
  }
}

async function initMilestones() {
  const container = document.getElementById("milestone-list");
  if (!container) return;

  let activeFilter = "all";
  const filterButtons = Array.from(document.querySelectorAll("[data-milestone-filter]"));

  const dialog = document.getElementById("gallery-dialog");
  const galleryTitle = document.getElementById("gallery-title");
  const galleryImage = document.getElementById("gallery-image");
  const galleryCounter = document.getElementById("gallery-counter");
  const gallerySource = document.getElementById("gallery-source");
  const prevButton = dialog?.querySelector("[data-gallery-prev]");
  const nextButton = dialog?.querySelector("[data-gallery-next]");

  let galleryImages = [];
  let galleryIndex = 0;

  const renderGallery = () => {
    if (!galleryImages.length || !galleryImage || !galleryCounter) return;
    const current = galleryImages[galleryIndex];
    galleryImage.src = current.file;
    galleryImage.alt = `Milestone image ${galleryIndex + 1}`;
    galleryCounter.textContent = `Image ${galleryIndex + 1} of ${galleryImages.length}`;
  };

  prevButton?.addEventListener("click", () => {
    if (!galleryImages.length) return;
    galleryIndex = (galleryIndex - 1 + galleryImages.length) % galleryImages.length;
    renderGallery();
  });

  nextButton?.addEventListener("click", () => {
    if (!galleryImages.length) return;
    galleryIndex = (galleryIndex + 1) % galleryImages.length;
    renderGallery();
  });

  try {
    const posts = await loadItems("assets/data/linkedin-posts.json", "__LINKEDIN_POSTS__");
    if (!Array.isArray(posts)) throw new Error("Invalid milestone data");

    const normalized = posts.map((post) => {
      const context = post.context || { date: "Milestone", category: "research" };
      const images = (post.images || []).filter((img) => !String(img.url || "").includes("static.licdn.com"));
      const summary = post.summary || "Professional milestone from research and academic progression.";
      const highlights = Array.isArray(post.highlights) ? post.highlights.slice(0, 3) : [];
      return { ...post, context, images, summary, highlights };
    });

    const render = () => {
      const list = normalized.filter((item) => (activeFilter === "all" ? true : item.context.category === activeFilter));

      if (!list.length) {
        container.innerHTML = '<p class="mono-note">No milestones match the selected category.</p>';
        return;
      }

      container.innerHTML = list
        .map((item) => {
          const first = item.images[0];
          const media = first
            ? `<img src="${first.file}" alt="${escapeHtml(item.title || "Milestone image")}" loading="lazy" />`
            : '<div class="milestone-empty-media">No public photo archived for this entry</div>';
          const bullets = item.highlights.length
            ? `<ul class="milestone-bullets">${item.highlights.map((point) => `<li>${escapeHtml(point)}</li>`).join("")}</ul>`
            : "";
          const actions = [
            item.images.length
              ? `<button class="button button-secondary" type="button" data-open-gallery="${item.id}">View Photos</button>`
              : "",
            `<a class="button button-secondary" href="${item.source_url}" target="_blank" rel="noopener">Original Post</a>`
          ]
            .filter(Boolean)
            .join("");
          return `
            <article class="milestone-card">
              ${media}
              <div class="milestone-head">
                <span class="milestone-date">${escapeHtml(item.context.date)}</span>
                <span class="milestone-category" data-category="${escapeHtml(item.context.category)}">${escapeHtml(item.context.category)}</span>
              </div>
              <h3>${escapeHtml(trimHeadline(item.title || "LinkedIn milestone"))}</h3>
              <p class="milestone-summary">${escapeHtml(item.summary)}</p>
              ${bullets}
              <div class="card-actions">${actions}</div>
            </article>
          `;
        })
        .join("");

      container.querySelectorAll("[data-open-gallery]").forEach((button) => {
        button.addEventListener("click", () => {
          const id = button.getAttribute("data-open-gallery");
          const item = list.find((entry) => entry.id === id);
          if (!item || !dialog || !galleryTitle || !gallerySource) return;
          galleryImages = item.images;
          galleryIndex = 0;
          galleryTitle.textContent = `${item.context.date} · ${item.context.summary}`;
          gallerySource.href = item.source_url;
          renderGallery();
          dialog.showModal();
        });
      });
    };

    filterButtons.forEach((button) => {
      button.addEventListener("click", () => {
        filterButtons.forEach((b) => b.classList.remove("is-active"));
        button.classList.add("is-active");
        activeFilter = button.dataset.milestoneFilter || "all";
        render();
      });
    });

    render();
  } catch (error) {
    container.innerHTML = '<p class="mono-note">Unable to load LinkedIn milestone data right now.</p>';
  }
}

function initEducationStepper() {
  const track = document.getElementById("education-track");
  if (!track) return;
  const prev = document.querySelector("[data-edu-prev]");
  const next = document.querySelector("[data-edu-next]");
  const step = () => Math.max(220, Math.round(track.clientWidth * 0.92));

  prev?.addEventListener("click", () => {
    track.scrollBy({ left: -step(), behavior: "smooth" });
  });
  next?.addEventListener("click", () => {
    track.scrollBy({ left: step(), behavior: "smooth" });
  });
}

async function loadItems(url, globalName) {
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  } catch (fetchError) {
    const fallback = window[globalName];
    if (Array.isArray(fallback)) return fallback;
    throw fetchError;
  }
}

function trimHeadline(text) {
  const cleaned = decodeBasicEntities(text)
    .replace(/\s*\|\s*LinkedIn.*$/i, "")
    .replace(/\s*\|\s*\d+\s*comments.*$/i, "");
  return cleaned.length > 110 ? `${cleaned.slice(0, 107)}...` : cleaned;
}

function decodeBasicEntities(value) {
  return String(value).replace(/&amp;/g, "&").replace(/&quot;/g, '"').replace(/&#39;/g, "'");
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
