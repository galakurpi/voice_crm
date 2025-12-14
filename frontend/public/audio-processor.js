class AudioProcessor extends AudioWorkletProcessor {
  process(inputs, outputs, parameters) {
    const input = inputs[0];
    if (input.length > 0) {
      const float32Data = input[0];
      this.port.postMessage(float32Data);
    }
    return true;
  }
}

registerProcessor('audio-processor', AudioProcessor);

