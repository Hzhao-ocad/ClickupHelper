class AudioRecorder {
  constructor() {
    this.stream = null;
    this.recorder = null;
    this.chunks = [];
    this.startTime = 0;
    this.audioCtx = null;
    this.analyser = null;
    this.analyserData = null;
  }

  async requestMicrophone() {
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    return this.stream;
  }

  createAnalyser() {
    this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    this.analyser = this.audioCtx.createAnalyser();
    this.analyser.fftSize = 64;
    const source = this.audioCtx.createMediaStreamSource(this.stream);
    source.connect(this.analyser);
    this.analyserData = new Uint8Array(this.analyser.frequencyBinCount);
  }

  getWaveformData() {
    if (!this.analyser) return null;
    this.analyser.getByteFrequencyData(this.analyserData);
    return this.analyserData;
  }

  getMimeType() {
    const types = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/wav',
    ];
    for (const t of types) {
      if (MediaRecorder.isTypeSupported(t)) return t;
    }
    return 'audio/webm';
  }

  start() {
    this.chunks = [];
    const mimeType = this.getMimeType();
    this.recorder = new MediaRecorder(this.stream, { mimeType });
    this.recorder.ondataavailable = (e) => {
      if (e.data.size > 0) this.chunks.push(e.data);
    };
    this.recorder.start(1000);
    this.startTime = Date.now();
  }

  stop() {
    return new Promise((resolve) => {
      this.recorder.onstop = () => {
        const blob = new Blob(this.chunks, { type: this.recorder.mimeType });
        resolve(blob);
      };
      this.recorder.stop();
    });
  }

  getElapsed() {
    return (Date.now() - this.startTime) / 1000;
  }

  cleanup() {
    if (this.stream) {
      this.stream.getTracks().forEach((t) => t.stop());
      this.stream = null;
    }
    if (this.audioCtx) {
      this.audioCtx.close().catch(() => {});
      this.audioCtx = null;
    }
    this.analyser = null;
    this.analyserData = null;
    this.recorder = null;
    this.chunks = [];
  }
}
