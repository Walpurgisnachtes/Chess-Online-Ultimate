class ModalManager {
  constructor() {
    this.modalEl = document.getElementById('globalModal');
    this.modal = new bootstrap.Modal(this.modalEl);
    this.titleEl = document.getElementById('globalModalLabel');
    this.bodyEl = document.getElementById('modalBody');
    this.footerEl = document.getElementById('modalFooter');
  }

  show() {
    // Remove visually-hidden, ensure correct ARIA
    this.modalEl.classList.remove("visually-hidden");
    this.modalEl.setAttribute("aria-modal", "true");
    this.modal.show();
  }

  hide() {
    this.modal.hide();
  }

  _onHidden(callback) {
    this.modalEl.addEventListener(
      "hidden.bs.modal",
      () => {
        this.modalEl.classList.add("visually-hidden");
        callback();
      },
      { once: true }
    );
  }

  error(message, title = "Error") {
    return new Promise((resolve) => {
      this.titleEl.textContent = title;
      this.bodyEl.innerHTML = `<p class="text-danger mb-0"><i class="fas fa-exclamation-triangle me-2"></i>${message}</p>`;
      this.footerEl.innerHTML = `
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
      `;
      this.modal.show();
      this.modalEl.addEventListener("hidden.bs.modal", () => resolve(), {
        once: true,
      });
    });
  }

  enterData(message, title = "Enter Name", defaultValue = "") {
    return new Promise((resolve) => {
      this.titleEl.textContent = title;
      this.bodyEl.innerHTML = `
        <div class="mb-3">
          <label class="form-label fw-medium">${message}</label>
          <input type="text" class="form-control" id="dataInput" value="${defaultValue}" autofocus>
        </div>
      `;

      this.footerEl.innerHTML = `
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
        <button type="button" class="btn btn-primary" id="dataConfirmBtn">OK</button>
      `;

      const input = document.getElementById('dataInput');
      const confirmBtn = document.getElementById('dataConfirmBtn');

      const submit = () => {
        const value = input.value.trim();
        this.modal.hide();
        resolve(value || null);
      };

      confirmBtn.onclick = submit;
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') submit();
      });

      this.modal._element.addEventListener('hidden.bs.modal', () => {
        resolve(null); // cancelled
      }, { once: true });

      this.modal.show();
      input.focus();
      input.select();
    });
  }

  messageOnly(message, title = "Notice") {
    return new Promise((resolve) => {
      this.titleEl.textContent = title;
      this.bodyEl.innerHTML = `<p class="mb-0">${message}</p>`;

      this.footerEl.innerHTML = `
        <button type="button" class="btn btn-primary" data-bs-dismiss="modal">OK</button>
      `;

      this.modal._element.addEventListener('hidden.bs.modal', () => resolve(), { once: true });
      this.modal.show();
    });
  }

  confirm(
    message,
    title = "Confirm Action",
    confirmText = "Confirm",
    danger = false
  ) {
    return new Promise((resolve) => {
      this.titleEl.textContent = title;
      this.bodyEl.innerHTML = `<p class="mb-0">${message}</p>`;

      const confirmClass = danger ? "btn-danger" : "btn-primary";
      this.footerEl.innerHTML = `
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
        <button type="button" class="btn ${confirmClass}" id="confirmYes">${confirmText}</button>
      `;

      const yesBtn = document.getElementById("confirmYes");
      const handler = () => {
        this.modal.hide();
        resolve(true);
      };
      yesBtn.onclick = handler;

      this.modalEl.addEventListener(
        "hidden.bs.modal",
        () => {
          yesBtn.onclick = null;
          resolve(false);
        },
        { once: true }
      );

      this.modal.show();
    });
  }

  promptConfirm(message, expectedValue, title = "Confirm Deletion") {
    return new Promise((resolve) => {
      this.titleEl.textContent = title;
      this.bodyEl.innerHTML = `
        <p class="mb-3">${message}</p>
        <div class="mb-3">
          <input type="text" class="form-control" id="confirmInput" placeholder="Type here...">
          <small class="text-muted">Type "<strong>${expectedValue}</strong>" to confirm</small>
        </div>
      `;

      this.footerEl.innerHTML = `
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
        <button type="button" class="btn btn-danger" id="confirmDeleteBtn" disabled>Delete Permanently</button>
      `;

      const input = document.getElementById("confirmInput");
      const deleteBtn = document.getElementById("confirmDeleteBtn");

      const check = () => {
        deleteBtn.disabled = input.value !== expectedValue;
      };

      input.addEventListener("input", check);

      deleteBtn.onclick = () => {
        this.modal.hide();
        resolve(true);
      };

      this.modalEl.addEventListener(
        "hidden.bs.modal",
        () => {
          input.removeEventListener("input", check);
          resolve(false);
        },
        { once: true }
      );

      this.modal.show();

      const focusHandler = () => {
        input.focus();
        check();
        this.modalEl.removeEventListener("shown.bs.modal", focusHandler);
      };
      this.modalEl.addEventListener("shown.bs.modal", focusHandler);
    });
  }
}

window.modal = new ModalManager();
