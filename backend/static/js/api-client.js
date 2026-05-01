class ApiClient {
  constructor() {
    this.sessionId = null;
  }

  async initSession() {
    const res = await fetch('/api/session/init', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{}',
    });
    if (!res.ok) throw new Error(`Session init failed: ${res.status}`);
    const data = await res.json();
    this.sessionId = data.session_id;
    return data;
  }

  async transcribeAudio(blob) {
    const form = new FormData();
    form.append('audio', blob, 'recording.webm');
    if (this.sessionId) form.append('session_id', this.sessionId);

    const res = await fetch('/api/transcribe', { method: 'POST', body: form });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Transcription failed: ${res.status}`);
    }
    return res.json();
  }

  async interpretTranscript(transcript) {
    const res = await fetch('/api/interpret', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: this.sessionId,
        transcript,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Interpretation failed: ${res.status}`);
    }
    return res.json();
  }

  async submitClarification(answers) {
    const res = await fetch('/api/clarify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: this.sessionId, answers }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Clarification failed: ${res.status}`);
    }
    return res.json();
  }

  async executeOperations(opIds, edits) {
    const res = await fetch('/api/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: this.sessionId,
        operation_ids: opIds,
        edits: edits || {},
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Execution failed: ${res.status}`);
    }
    return res.json();
  }
}
