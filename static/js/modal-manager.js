class ModalManager {
  constructor() {
    this.modalEl = document.getElementById("globalModal");
    this.modal = new bootstrap.Modal(this.modalEl);
    this.titleEl = document.getElementById("globalModalLabel");
    this.bodyEl = document.getElementById("modalBody");
    this.footerEl = document.getElementById("modalFooter");
  }

  show() {
    this.modalEl.setAttribute("aria-modal", "true");
    this.modal.show();
  }

  removeFocus() {
    const currentActiveElement = document.activeElement;
    currentActiveElement.blur();
  }

  hide() {
    removeFocus();
    this.modal.hide();
  }

  error(message, title = "Error") {
    return new Promise((resolve) => {
      this.titleEl.textContent = title;
      this.bodyEl.innerHTML = `<p class="text-danger mb-0"><i class="fas fa-exclamation-triangle me-2"></i>${message}</p>`;
      this.footerEl.innerHTML = `
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
      `;
      this.show();
      this.modalEl.addEventListener(
        "hidden.bs.modal",
        () => {
          this.removeFocus();
          resolve();
        },
        {
          once: true,
        }
      );
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

      const input = document.getElementById("dataInput");
      const confirmBtn = document.getElementById("dataConfirmBtn");

      const submit = () => {
        const value = input.value.trim();
        this.hide();
        resolve(value || null);
      };

      confirmBtn.onclick = submit;
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") submit();
      });

      this.modal._element.addEventListener(
        "hidden.bs.modal",
        () => {
          this.removeFocus();
          resolve();
        },
        { once: true }
      );

      this.show();
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

      this.modal._element.addEventListener(
        "hidden.bs.modal",
        () => {
          this.removeFocus();
          resolve();
        },
        {
          once: true,
        }
      );
      this.show();
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
        this.hide();
        resolve(true);
      };
      yesBtn.onclick = handler;

      this.modalEl.addEventListener(
        "hidden.bs.modal",
        () => {
          this.removeFocus();
          yesBtn.onclick = null;
          resolve(false);
        },
        { once: true }
      );

      this.show();
    });
  }
}

window.modal = new ModalManager();
