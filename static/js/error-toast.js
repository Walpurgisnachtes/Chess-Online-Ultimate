class ErrorToastManager {
  constructor() {
    this.errorOverlay = document.getElementById("errorOverlay");
    this.errorText = document.getElementById("errorText");

    this.errorOverlay.addEventListener("click", (e) => {
      if (e.target === errorOverlay) {
        this.errorOverlay.classList.remove('show');
      }
    });
  }

  showError(message, duration = 2000) {
    this.errorText.textContent = message;
    
    // Reset state
    this.errorOverlay.classList.remove('show');
    void errorOverlay.offsetWidth; // force reflow

    // Show with fade-in
    this.errorOverlay.classList.add('show');

    // Auto fade-out + hide
    setTimeout(() => {
      this.errorOverlay.classList.remove('show');
      // Optional: fully hide after transition ends
      this.errorOverlay.addEventListener('transitionend', function handler() {
        this.errorOverlay.style.display = 'none';
        this.errorOverlay.removeEventListener('transitionend', handler);
      });
    }, duration);
  }
}

// Start when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  window.errorToastManager = new ErrorToastManager();
});
