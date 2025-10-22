// Theme management script
document.addEventListener('DOMContentLoaded', () => {
  const themeToggle = document.getElementById('themeToggle');
  const sunIcon = document.getElementById('sunIcon');
  const moonIcon = document.getElementById('moonIcon');
  const body = document.body;

  // Load saved theme or default to dark
  const savedTheme = localStorage.getItem('theme') || 'dark';
  body.className = savedTheme;
  updateIcon();

  // Theme toggle event
  themeToggle.addEventListener('click', () => {
    const newTheme = body.classList.contains('dark') ? 'light' : 'dark';
    body.className = newTheme;
    localStorage.setItem('theme', newTheme);
    updateIcon();
  });

  function updateIcon() {
    if (body.classList.contains('dark')) {
      sunIcon.style.display = 'block';
      moonIcon.style.display = 'none';
    } else {
      sunIcon.style.display = 'none';
      moonIcon.style.display = 'block';
    }
  }

  // Loading animation
  const progressFill = document.getElementById('progress-fill');
  const progressPercent = document.getElementById('progress-percent');
  const loadingScreen = document.getElementById('loading-screen');
  const mainContent = document.getElementById('main-content');

  let progress = 0;
  const progressInterval = setInterval(() => {
    progress += 2;
    progressFill.style.width = progress + '%';
    progressPercent.textContent = progress + '%';

    if (progress >= 100) {
      clearInterval(progressInterval);
      setTimeout(() => {
        loadingScreen.classList.add('hidden');
        mainContent.style.display = 'block';
        mainContent.classList.add('fade-in');
      }, 300);
    }
  }, 20);
});
