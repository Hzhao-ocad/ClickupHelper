class UIManager {
  constructor() {
    this.views = {};
    this.timerInterval = null;
    this.waveformInterval = null;
    this._initViews();
  }

  _initViews() {
    const names = ['idle', 'recording', 'processing', 'preview', 'clarify', 'result', 'error'];
    for (const name of names) {
      this.views[name] = document.getElementById(`view-${name}`);
    }
  }

  setState(state, data) {
    this._hideAll();
    this._stopWaveform();
    this._stopTimer();
    const view = this.views[state];
    if (view) view.classList.add('active');

    switch (state) {
      case 'idle': this._renderIdle(data); break;
      case 'recording': this._renderRecording(data); break;
      case 'processing': this._renderProcessing(data); break;
      case 'preview': this._renderPreview(data); break;
      case 'clarify': this._renderClarify(data); break;
      case 'result': this._renderResult(data); break;
      case 'error': this._renderError(data); break;
    }
  }

  _hideAll() {
    for (const v of Object.values(this.views)) {
      if (v) v.classList.remove('active');
    }
  }

  _renderIdle(data) {
    const btn = document.getElementById('mic-button');
    if (btn) btn.classList.remove('recording');

    if (data && data.transcript) {
      const textarea = document.getElementById('idle-transcript-input');
      const submitBtn = document.getElementById('idle-submit');
      const clearBtn = document.getElementById('idle-clear');
      if (textarea) textarea.value = data.transcript;
      if (submitBtn) submitBtn.disabled = false;
      if (clearBtn) clearBtn.style.display = '';
    }

    if (data && data.workspaceName) {
      document.getElementById('workspace-indicator').textContent = `Workspace: ${data.workspaceName}`;
    }
  }

  _renderRecording(data) {
    const btn = document.getElementById('mic-button');
    if (btn) btn.classList.add('recording');
    this._startTimer();
  }

  _renderProcessing(data) {
    const stage = document.getElementById('processing-stage');
    if (stage && data && data.stage) {
      stage.textContent = data.stage;
    } else if (stage) {
      stage.textContent = 'Processing...';
    }
  }

_renderPreview(data) {
    const container = document.getElementById('preview-cards');
    if (!container) return;
    container.innerHTML = '';

    if (!data.operations || data.operations.length === 0) {
      container.innerHTML = '<p>No operations detected.</p>';
      return;
    }

    for (const op of data.operations) {
      const card = document.createElement('div');
      card.className = `card ${op.type || ''}`;

      const typeLabel = (op.type || '').replace(/_/g, ' ');
      const paramsHtml = op.params
        ? Object.entries(op.params)
            .map(([k, v]) => `<span>${k.replace(/_/g, ' ')}: ${v}</span>`)
            .join('')
        : '';

      card.innerHTML = `
        <div class="card-header">
          <span class="card-type ${op.type || ''}">${typeLabel}</span>
          <button class="btn btn-secondary" data-action="edit" data-op-id="${op.id}" style="padding:4px 12px;font-size:0.8rem;">Edit</button>
        </div>
        <div class="card-summary">${op.summary || 'Operation'}</div>
        ${paramsHtml ? `<div class="card-params">${paramsHtml}</div>` : ''}
      `;
      container.appendChild(card);
    }
  }

  _renderClarify(data) {
    const container = document.getElementById('clarify-cards');
    if (!container) return;
    container.innerHTML = '';

    if (!data.questions || data.questions.length === 0) {
      container.innerHTML = '<p>No questions needed.</p>';
      return;
    }

    for (const q of data.questions) {
      const div = document.createElement('div');
      div.className = 'clarify-question';
      const id = q.id || q.question;

      let input = '';
      if (q.options && q.options.length > 0) {
        input = `<select name="${id}">${q.options.map((o) => `<option value="${o}">${o}</option>`).join('')}</select>`;
      } else if (q.answer_type === 'date') {
        input = `<input type="date" name="${id}">`;
      } else {
        input = `<input type="text" name="${id}" placeholder="Your answer...">`;
      }

      div.innerHTML = `<label>${q.question}</label>${input}`;
      container.appendChild(div);
    }
  }

  _renderResult(data) {
    const container = document.getElementById('result-cards');
    if (!container) return;
    container.innerHTML = '';

    for (const r of data.results || []) {
      const card = document.createElement('div');
      card.className = `card ${r.status === 'success' ? 'success' : 'failure'}`;

      const statusLabel = r.status === 'success' ? 'SUCCESS' : 'FAILED';
      let linkHtml = '';
      if (r.clickup_url) {
        linkHtml = `<a href="${r.clickup_url}" target="_blank" style="color:var(--primary);font-size:0.85rem;">Open in ClickUp &nearr;</a>`;
      }

      card.innerHTML = `
        <div class="card-header">
          <span class="card-type ${r.status === 'success' ? 'success' : 'failure'}">${statusLabel}</span>
        </div>
        <div class="card-summary">${r.summary || r.error || 'Done'}</div>
        ${linkHtml}
      `;
      container.appendChild(card);
    }
  }

  _renderError(data) {
    const container = document.getElementById('error-content');
    if (!container) return;
    const msg = data && data.message ? data.message : 'An unexpected error occurred.';
    const detail = data && data.detail ? `<p style="font-size:0.85rem;color:var(--text-muted);margin-top:8px;">${data.detail}</p>` : '';
    container.innerHTML = `<p><strong>Error:</strong> ${msg}</p>${detail}`;
  }

  // ── Waveform visualization ────────────────────────────────────

  startWaveform(getDataFn) {
    this._stopWaveform();
    const canvas = document.getElementById('waveform-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    this.waveformInterval = setInterval(() => {
      const data = getDataFn();
      if (!data) return;
      ctx.clearRect(0, 0, width, height);

      const barWidth = width / data.length;
      const barMargin = 2;
      for (let i = 0; i < data.length; i++) {
        const barHeight = (data[i] / 255) * height;
        const x = i * barWidth + barMargin / 2;
        const y = (height - barHeight) / 2;

        const gradient = ctx.createLinearGradient(0, height, 0, 0);
        gradient.addColorStop(0, '#E74C3C');
        gradient.addColorStop(0.5, '#F39C12');
        gradient.addColorStop(1, '#2ECC71');

        ctx.fillStyle = gradient;
        ctx.fillRect(x, y, barWidth - barMargin, barHeight);
      }
    }, 50);
  }

  _stopWaveform() {
    if (this.waveformInterval) {
      clearInterval(this.waveformInterval);
      this.waveformInterval = null;
    }
    const canvas = document.getElementById('waveform-canvas');
    if (canvas) {
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
  }

  // ── Timer ─────────────────────────────────────────────────────

  _startTimer() {
    this._stopTimer();
    let elapsed = 0;
    const display = document.getElementById('recording-timer');
    this.timerInterval = setInterval(() => {
      elapsed++;
      const mins = Math.floor(elapsed / 60);
      const secs = elapsed % 60;
      if (display) display.textContent = `${mins}:${secs.toString().padStart(2, '0')}`;
    }, 1000);
  }

  _stopTimer() {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
  }

  showWorkspace(name) {
    const el = document.getElementById('workspace-indicator');
    if (el) el.textContent = `Workspace: ${name}`;
  }

  // ── Toast notification ────────────────────────────────────────

  showToast(message, duration = 3000) {
    let toast = document.getElementById('toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'toast';
      toast.style.cssText = `
        position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
        background: var(--text); color: white; padding: 12px 24px;
        border-radius: 8px; font-size: 0.9rem; z-index: 1000;
        opacity: 0; transition: opacity 0.3s;
      `;
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.style.opacity = '1';
    clearTimeout(this._toastTimeout);
    this._toastTimeout = setTimeout(() => {
      toast.style.opacity = '0';
    }, duration);
  }
}
