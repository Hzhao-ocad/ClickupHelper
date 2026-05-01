class App {
  constructor() {
    this.state = 'idle';
    this.recorder = new AudioRecorder();
    this.api = new ApiClient();
    this.ui = new UIManager();
    this.pendingOperations = [];
    this.pendingClarification = null;

    this.micButton = document.getElementById('mic-button');
    this.idleTranscriptInput = document.getElementById('idle-transcript-input');
    this.idleSubmitBtn = document.getElementById('idle-submit');
    this.idleClearBtn = document.getElementById('idle-clear');
    this.approveAllBtn = document.getElementById('approve-all');
    this.cancelPreviewBtn = document.getElementById('cancel-preview');
    this.clarifySubmitBtn = document.getElementById('clarify-submit');
    this.newRecordingBtn = document.getElementById('new-recording');
    this.retryBtn = document.getElementById('error-retry');

    this._bindEvents();
    this._init();
  }

  async _init() {
    try {
      const data = await this.api.initSession();
      if (data.workspace_context) {
        this.ui.showWorkspace(data.workspace_context.name || '');
      }
    } catch (err) {
      console.warn('Session init failed, continuing without workspace context:', err);
    }
  }

  _bindEvents() {
    // Mic button: press and hold to record, release to stop
    this.micButton.addEventListener('mousedown', () => this._startRecording());
    this.micButton.addEventListener('mouseup', () => this._stopRecording());
    this.micButton.addEventListener('mouseleave', () => {
      if (this.state === 'recording') this._stopRecording();
    });

    // Touch events for mobile
    this.micButton.addEventListener('touchstart', (e) => { e.preventDefault(); this._startRecording(); });
    this.micButton.addEventListener('touchend', (e) => { e.preventDefault(); this._stopRecording(); });

    // Keyboard: hold Space to record (only when textarea is not focused)
    document.addEventListener('keydown', (e) => {
      if (e.code === 'Space' && this.state === 'idle' && document.activeElement !== this.idleTranscriptInput) {
        e.preventDefault();
        this._startRecording();
      }
    });
    document.addEventListener('keyup', (e) => {
      if (e.code === 'Space' && this.state === 'recording') {
        e.preventDefault();
        this._stopRecording();
      }
    });

    // Idle input area
    if (this.idleSubmitBtn) {
      this.idleSubmitBtn.addEventListener('click', () => this._submitFromIdle());
    }
    if (this.idleClearBtn) {
      this.idleClearBtn.addEventListener('click', () => this._clearInput());
    }

    // Auto-enable submit button when user types
    if (this.idleTranscriptInput) {
      const updateSubmitState = () => {
        const hasText = this.idleTranscriptInput.value.trim().length > 0;
        if (this.idleSubmitBtn) this.idleSubmitBtn.disabled = !hasText;
        if (this.idleClearBtn) this.idleClearBtn.style.display = hasText ? '' : 'none';
      };
      this.idleTranscriptInput.addEventListener('input', updateSubmitState);
      this.idleTranscriptInput.addEventListener('keyup', updateSubmitState);

      // Enter submits from textarea (without Shift)
      this.idleTranscriptInput.addEventListener('keydown', (e) => {
        if (e.code === 'Enter' && !e.shiftKey && this.state === 'idle') {
          e.preventDefault();
          this._submitFromIdle();
        }
      });
    }

    // Preview actions
    this.approveAllBtn.addEventListener('click', () => this._approveAll());
    this.cancelPreviewBtn.addEventListener('click', () => this._cancel());

    // Per-operation edit buttons (event delegation)
    document.getElementById('preview-cards').addEventListener('click', (e) => {
      const btn = e.target.closest('[data-action]');
      if (!btn) return;
      const opId = btn.dataset.opId;
      if (btn.dataset.action === 'edit') this._editOperation(opId);
    });

    // Clarify
    this.clarifySubmitBtn.addEventListener('click', () => this._submitClarification());

    // Result
    this.newRecordingBtn.addEventListener('click', () => this._resetToIdle());

    // Error retry
    this.retryBtn.addEventListener('click', () => this._retry());

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      if (e.code === 'Enter' && this.state === 'preview') { e.preventDefault(); this._approveAll(); }
      if (e.code === 'Escape' && (this.state === 'preview' || this.state === 'error')) { e.preventDefault(); this._cancel(); }
    });
  }

  async _startRecording() {
    if (this.state !== 'idle') return;
    try {
      await this.recorder.requestMicrophone();
      this.recorder.createAnalyser();
      this.recorder.start();
      this.state = 'recording';
      this.ui.setState('recording');
      this.ui.startWaveform(() => this.recorder.getWaveformData());
    } catch (err) {
      this.ui.setState('error', {
        message: 'Microphone access denied. Please allow microphone access in your browser settings and try again.',
      });
    }
  }

  async _stopRecording() {
    if (this.state !== 'recording') return;
    const blob = await this.recorder.stop();
    this.recorder.cleanup();
    this.state = 'processing';
    this.ui.setState('processing', { stage: 'Transcribing audio...' });
    await this._transcribeAudio(blob);
  }

  async _transcribeAudio(blob) {
    try {
      this.ui.setState('processing', { stage: 'Transcribing audio...' });
      const transcriptData = await this.api.transcribeAudio(blob);

      if (!transcriptData.transcript || transcriptData.transcript.trim() === '') {
        this.ui.setState('error', { message: "I didn't catch that. Please try speaking again." });
        this.state = 'error';
        return;
      }

      // Populate the idle textarea with the transcript and return to idle
      this.state = 'idle';
      this.ui.setState('idle', { transcript: transcriptData.transcript });
    } catch (err) {
      this.state = 'error';
      this.ui.setState('error', { message: err.message || 'Transcription failed.' });
    }
  }

  async _submitFromIdle() {
    if (this.state !== 'idle') return;
    const input = this.idleTranscriptInput;
    if (!input) return;
    const transcript = input.value.trim();
    if (!transcript) return;

    this.state = 'processing';
    this.ui.setState('processing', { stage: 'Interpreting your request...' });
    await this._interpretTranscript(transcript);
  }

  _clearInput() {
    this.idleTranscriptInput.value = '';
    this.idleSubmitBtn.disabled = true;
    this.idleClearBtn.style.display = 'none';
    this.idleTranscriptInput.focus();
  }

  async _interpretTranscript(transcript) {
    try {
      const interpretData = await this.api.interpretTranscript(transcript);

      if (interpretData.requires_clarification) {
        this.pendingClarification = interpretData.clarification_questions;
        this.state = 'clarify';
        this.ui.setState('clarify', { questions: interpretData.clarification_questions });
      } else {
        this.pendingOperations = interpretData.operations || [];
        this.state = 'preview';
        this.ui.setState('preview', { operations: this.pendingOperations });
      }
    } catch (err) {
      this.state = 'error';
      this.ui.setState('error', { message: err.message || 'Interpretation failed.' });
    }
  }

  async _approveAll() {
    if (this.state !== 'preview') return;
    const opIds = this.pendingOperations.map((op) => op.id);
    await this._execute(opIds);
  }

  async _execute(opIds, edits = null) {
    this.state = 'processing';
    this.ui.setState('processing', { stage: 'Executing operations...' });
    try {
      const result = await this.api.executeOperations(opIds, edits);
      this.state = 'result';
      this.ui.setState('result', result);
    } catch (err) {
      this.state = 'error';
      this.ui.setState('error', { message: err.message || 'Execution failed.' });
    }
  }

  async _submitClarification() {
    if (this.state !== 'clarify') return;
    const answers = {};
    const inputs = document.querySelectorAll('#clarify-cards input, #clarify-cards select');
    inputs.forEach((input) => {
      answers[input.name] = input.value;
    });

    this.state = 'processing';
    this.ui.setState('processing', { stage: 'Interpreting with clarifications...' });
    try {
      const data = await this.api.submitClarification(answers);

      if (data.requires_clarification) {
        this.pendingClarification = data.clarification_questions;
        this.state = 'clarify';
        this.ui.setState('clarify', { questions: data.clarification_questions });
      } else {
        this.pendingOperations = data.operations || [];
        this.state = 'preview';
        this.ui.setState('preview', { operations: this.pendingOperations });
      }
    } catch (err) {
      this.state = 'error';
      this.ui.setState('error', { message: err.message || 'Clarification failed.' });
    }
  }

  _editOperation(opId) {
    const op = this.pendingOperations.find((o) => o.id === opId);
    if (!op) return;
    const newName = prompt('Edit task name:', op.params.name || op.params.title || '');
    if (newName !== null && newName.trim() !== '') {
      if (op.params.name !== undefined) {
        op.params.name = newName.trim();
      } else if (op.params.title !== undefined) {
        op.params.title = newName.trim();
      }
      op.summary = op.summary.replace(/'.*?'/, `'${newName.trim()}'`);
      this.ui.setState('preview', { operations: this.pendingOperations });
    }
  }

  _cancel() {
    this._resetToIdle();
  }

  _resetToIdle() {
    this.state = 'idle';
    this.pendingOperations = [];
    this.pendingClarification = null;
    this.idleTranscriptInput.value = '';
    this.idleSubmitBtn.disabled = true;
    this.idleClearBtn.style.display = 'none';
    this.ui.setState('idle');
  }

  _retry() {
    this._resetToIdle();
  }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  window.app = new App();
});
