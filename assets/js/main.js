(() => {
  const yearNodes = document.querySelectorAll("[data-year]");
  const currentYear = new Date().getFullYear();
  yearNodes.forEach((node) => {
    node.textContent = String(currentYear);
  });

  const toggleButton = document.querySelector("[data-menu-toggle]");
  const nav = document.getElementById("site-navigation");

  if (!toggleButton || !nav) {
    return;
  }

  const closeMenu = () => {
    nav.dataset.open = "false";
    toggleButton.setAttribute("aria-expanded", "false");
  };

  const openMenu = () => {
    nav.dataset.open = "true";
    toggleButton.setAttribute("aria-expanded", "true");
  };

  toggleButton.addEventListener("click", () => {
    const isOpen = nav.dataset.open === "true";
    if (isOpen) {
      closeMenu();
    } else {
      openMenu();
    }
  });

  nav.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => closeMenu());
  });

  window.addEventListener("resize", () => {
    if (window.innerWidth > 760) {
      nav.dataset.open = "";
      toggleButton.setAttribute("aria-expanded", "false");
    }
  });

  document.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof Node)) {
      return;
    }
    if (!nav.contains(target) && !toggleButton.contains(target)) {
      closeMenu();
    }
  });
})();
