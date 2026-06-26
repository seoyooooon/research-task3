// popup.js
// Handles opening URLs inside Chrome Extension popups safely

document.addEventListener('DOMContentLoaded', () => {
  const links = document.querySelectorAll('.btn-link');
  
  links.forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const url = link.getAttribute('href');
      if (url) {
        chrome.tabs.create({ url: url });
      }
    });
  });
});
