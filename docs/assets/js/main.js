(() => {
  const yearNodes = document.querySelectorAll("[data-year]");
  const currentYear = new Date().getFullYear();
  yearNodes.forEach((node) => {
    node.textContent = String(currentYear);
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
      if (isOpen) {
        closeMenu();
      } else {
        openMenu();
      }
    });

    document.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof Node)) {
        return;
      }
      if (!nav.contains(target) && !toggle.contains(target)) {
        closeMenu();
      }
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

  const links = Array.from(document.querySelectorAll('.site-nav a[href^="#"]'));
  if (!links.length) {
    return;
  }

  const sectionIds = links
    .map((link) => link.getAttribute("href"))
    .filter((href) => href && href.startsWith("#"))
    .map((href) => href.replace("#", ""));

  const sections = sectionIds
    .map((id) => document.getElementById(id))
    .filter((section) => section instanceof HTMLElement);

  if (!sections.length) {
    return;
  }

  const linkById = new Map();
  links.forEach((link) => {
    const href = link.getAttribute("href");
    if (!href) return;
    linkById.set(href.replace("#", ""), link);
  });

  const setActive = (id) => {
    links.forEach((link) => link.classList.remove("is-active"));
    const activeLink = linkById.get(id);
    if (activeLink) {
      activeLink.classList.add("is-active");
    }
  };

  const observer = new IntersectionObserver(
    (entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
      if (visible.length > 0) {
        setActive(visible[0].target.id);
      }
    },
    {
      rootMargin: "-40% 0px -45% 0px",
      threshold: [0.2, 0.4, 0.6]
    }
  );

  sections.forEach((section) => observer.observe(section));
})();
