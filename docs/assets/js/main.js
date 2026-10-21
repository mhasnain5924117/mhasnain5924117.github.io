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
      if (window.innerWidth > 940) {
        nav.dataset.open = "";
        toggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  initSectionSpy();
  initFilms();
})();

function initFilms() {
  const player = document.getElementById("film-player");
  const items = Array.from(document.querySelectorAll(".film-item[data-film]"));
  if (!(player instanceof HTMLVideoElement) || !items.length) return;

  const narration = document.getElementById("film-narration");
  const title = document.getElementById("film-title");
  const sub = document.getElementById("film-sub");
  const meta = document.getElementById("film-meta");
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  let current = items.findIndex((item) => item.classList.contains("is-active"));
  if (current < 0) current = 0;
  let userPaused = false;
  let programmaticPause = false;

  const setProgress = (item, value) => {
    item.style.setProperty("--progress", String(Math.max(0, Math.min(1, value))));
  };

  const setNarration = (text) => {
    if (!narration) return;
    if (narration.textContent.trim() === text.trim()) return;
    narration.classList.add("is-fading");
    window.setTimeout(() => {
      narration.textContent = text;
      narration.classList.remove("is-fading");
    }, reducedMotion ? 0 : 180);
  };

  const attachCaptions = () => {
    const track = player.textTracks && player.textTracks[0];
    if (!track) return;
    track.mode = "hidden";
    track.oncuechange = () => {
      const cue = track.activeCues && track.activeCues[0];
      if (cue && "text" in cue) setNarration(String(cue.text));
    };
  };

  const load = (index, { autoplay = false } = {}) => {
    const item = items[index];
    if (!item) return;
    current = index;

    items.forEach((other, i) => {
      const active = i === index;
      other.classList.toggle("is-active", active);
      other.setAttribute("aria-pressed", active ? "true" : "false");
      if (!active) setProgress(other, 0);
    });

    const { src, vtt, poster, title: filmTitle, sub: filmSub, links, hd } = item.dataset;

    if (!player.paused) {
      programmaticPause = true;
      player.pause();
    }
    player.poster = poster || "";
    player.setAttribute("aria-label", `Research film: ${filmTitle || ""}`);

    const source = player.querySelector("source");
    if (source && src) source.setAttribute("src", src);
    const track = player.querySelector("track");
    if (track && vtt) track.setAttribute("src", vtt);
    player.load();
    attachCaptions();

    if (title && filmTitle) title.textContent = filmTitle;
    if (sub && filmSub) sub.textContent = filmSub;
    if (narration) narration.textContent = filmSub || "";

    if (meta) {
      meta.textContent = "";
      let parsed = [];
      try {
        parsed = links ? JSON.parse(links) : [];
      } catch (error) {
        parsed = [];
      }
      parsed.forEach((entry) => {
        if (!entry || !entry.href || !entry.label) return;
        const a = document.createElement("a");
        a.href = entry.href;
        a.textContent = entry.label;
        if (/^https?:/i.test(entry.href)) {
          a.target = "_blank";
          a.rel = "noopener";
        }
        meta.appendChild(a);
      });
      if (hd) {
        const a = document.createElement("a");
        a.href = hd;
        a.textContent = "Full HD (MP4)";
        a.setAttribute("download", "");
        meta.appendChild(a);
      }
    }

    if (autoplay) {
      const attempt = player.play();
      if (attempt && typeof attempt.catch === "function") attempt.catch(() => {});
    }
  };

  items.forEach((item, index) => {
    item.addEventListener("click", () => {
      userPaused = false;
      load(index, { autoplay: true });
    });
  });

  player.addEventListener("timeupdate", () => {
    const item = items[current];
    if (!item || !player.duration) return;
    setProgress(item, player.currentTime / player.duration);
  });

  player.addEventListener("ended", () => {
    const item = items[current];
    if (item) setProgress(item, 1);
    if (userPaused) return;
    const next = (current + 1) % items.length;
    window.setTimeout(() => load(next, { autoplay: true }), reducedMotion ? 0 : 500);
  });

  player.addEventListener("pause", () => {
    if (programmaticPause) {
      programmaticPause = false;
      return;
    }
    if (!player.ended && !player.seeking) userPaused = true;
  });
  player.addEventListener("play", () => {
    userPaused = false;
  });

  attachCaptions();

  // Hero and project-card links jump to a specific film.
  document.querySelectorAll("[data-film-link]").forEach((link) => {
    link.addEventListener("click", (event) => {
      const id = link.getAttribute("data-film-link");
      const index = items.findIndex((item) => item.dataset.film === id);
      if (index < 0) return;
      event.preventDefault();
      const section = document.getElementById("films");
      if (section) section.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "start" });
      userPaused = false;
      load(index, { autoplay: true });
      if (window.history && window.history.replaceState) window.history.replaceState(null, "", "#films");
    });
  });

  // Start the first film silently once the theater scrolls into view.
  if (!reducedMotion && "IntersectionObserver" in window) {
    let started = false;
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && !started && !userPaused && player.paused) {
            started = true;
            const attempt = player.play();
            if (attempt && typeof attempt.catch === "function") attempt.catch(() => {});
          }
          if (!entry.isIntersecting && !player.paused) {
            programmaticPause = true;
            player.pause();
            started = false;
          }
        });
      },
      { threshold: 0.45 }
    );
    observer.observe(player);
  }
}

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
