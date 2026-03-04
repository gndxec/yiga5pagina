document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
  anchor.addEventListener('click', (event) => {
    const targetId = anchor.getAttribute('href');
    const section = document.querySelector(targetId);

    if (!section) {
      return;
    }

    event.preventDefault();
    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
});
