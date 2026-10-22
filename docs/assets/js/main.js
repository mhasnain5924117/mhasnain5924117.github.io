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
  initAnimations();
  initProjectMedia();
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

function initAnimations() {
  const dialog = document.getElementById("animation-dialog");
  const player = document.getElementById("animation-player");
  const openers = Array.from(document.querySelectorAll("[data-animation-open]"));
  if (!(dialog instanceof HTMLDialogElement) || !(player instanceof HTMLVideoElement) || !openers.length) return;

  const narration = document.getElementById("animation-narration");
  const title = document.getElementById("animation-title");
  const sub = document.getElementById("animation-sub");
  const links = document.getElementById("animation-links");
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let opener = null;

  const setNarration = (text) => {
    if (!narration) return;
    if (narration.textContent.trim() === text.trim()) return;
    narration.classList.add("is-fading");
    window.setTimeout(() => {
      narration.textContent = text;
      narration.classList.remove("is-fading");
    }, reducedMotion ? 0 : 160);
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

  const open = (button) => {
    const { src, vtt, poster, title: animTitle, sub: animSub, links: linkJson, hd } = button.dataset;
    opener = button;
    // Pause any in-card animation so two copies never run at once.
    document.querySelectorAll("video.project-video").forEach((video) => video.pause());

    const source = player.querySelector("source");
    if (source && src) source.setAttribute("src", src);
    const track = player.querySelector("track");
    if (track && vtt) track.setAttribute("src", vtt);
    player.poster = poster || "";
    player.setAttribute("aria-label", animTitle || "Research animation");
    player.load();
    attachCaptions();

    if (title) title.textContent = animTitle || "";
    if (sub) sub.textContent = animSub || "";
    if (narration) narration.textContent = animSub || "";

    if (links) {
      links.textContent = "";
      let parsed = [];
      try {
        parsed = linkJson ? JSON.parse(linkJson) : [];
      } catch (error) {
        parsed = [];
      }
      parsed.forEach((entry) => {
        if (!entry || !entry.href || !entry.label) return;
        const a = document.createElement("a");
        a.href = entry.href;
        a.textContent = entry.label;
        a.target = "_blank";
        a.rel = "noopener";
        links.appendChild(a);
      });
      if (hd) {
        const a = document.createElement("a");
        a.href = hd;
        a.textContent = "Download full HD (MP4)";
        a.setAttribute("download", "");
        links.appendChild(a);
      }
    }

    if (!dialog.open) dialog.showModal();
    document.documentElement.style.overflow = "hidden";
    const attempt = player.play();
    if (attempt && typeof attempt.catch === "function") attempt.catch(() => {});
  };

  const close = () => {
    if (dialog.open) dialog.close();
  };

  dialog.addEventListener("close", () => {
    player.pause();
    document.documentElement.style.overflow = "";
    if (opener && typeof opener.focus === "function") opener.focus({ preventScroll: true });
  });

  dialog.addEventListener("click", (event) => {
    // Clicks on the backdrop land on the <dialog> itself, not on its children.
    if (event.target === dialog) close();
  });

  dialog.querySelectorAll("[data-anim-close]").forEach((button) => {
    button.addEventListener("click", close);
  });

  openers.forEach((button) => {
    button.addEventListener("click", () => open(button));
  });
}

function initProjectMedia() {
  const cards = Array.from(document.querySelectorAll(".project-card-media"));
  if (!cards.length) return;
  const videos = cards.map((card) => card.querySelector("video.project-video")).filter(Boolean);

  cards.forEach((card) => {
    const video = card.querySelector("video.project-video");
    const figure = card.querySelector(".project-figure");
    const narration = card.querySelector(".project-narration");
    const buttons = Array.from(card.querySelectorAll(".media-switch button[data-media]"));
    if (!video || !figure || !buttons.length) return;

    // Captions are shown as a narration line under the video instead of over it.
    const track = video.textTracks && video.textTracks[0];
    if (track && narration) {
      track.mode = "hidden";
      track.addEventListener("cuechange", () => {
        const cue = track.activeCues && track.activeCues[0];
        const text = cue && "text" in cue ? String(cue.text) : "";
        if (narration.textContent === text) return;
        narration.classList.add("is-fading");
        window.setTimeout(() => {
          narration.textContent = text;
          narration.classList.remove("is-fading");
        }, 150);
      });
    }

    const show = (mode) => {
      const showFigure = mode === "figure";
      figure.hidden = !showFigure;
      video.hidden = showFigure;
      if (narration) narration.hidden = showFigure;
      if (showFigure) video.pause();
      buttons.forEach((button) => {
        const active = button.dataset.media === mode;
        button.classList.toggle("is-active", active);
        button.setAttribute("aria-pressed", active ? "true" : "false");
      });
    };

    buttons.forEach((button) => {
      button.addEventListener("click", () => show(button.dataset.media || "animation"));
    });
  });

  // Only one card animation plays at a time.
  videos.forEach((video) => {
    video.addEventListener("play", () => {
      videos.forEach((other) => {
        if (other !== video && !other.paused) other.pause();
      });
    });
  });
}
