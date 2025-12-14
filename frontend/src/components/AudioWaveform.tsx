import React, { useEffect, useRef, useState } from 'react';

interface AudioWaveformProps {
  stream: MediaStream | null;
  isActive: boolean;
}

const AudioWaveform: React.FC<AudioWaveformProps> = ({ stream, isActive }) => {
  const [waveformData, setWaveformData] = useState<number[]>(new Array(60).fill(0));
  const analyserRef = useRef<AnalyserNode | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  useEffect(() => {
    if (!stream || !isActive) {
      setWaveformData(new Array(60).fill(0));
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      return;
    }

    // Create a separate audio context for visualization
    const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    audioContextRef.current = audioContext;

    // Create analyser node
    const analyser = audioContext.createAnalyser();
    analyser.fftSize = 256;
    analyser.smoothingTimeConstant = 0.8;
    analyserRef.current = analyser;

    // Connect stream to analyser
    const source = audioContext.createMediaStreamSource(stream);
    source.connect(analyser);

    // Update waveform
    const updateWaveform = () => {
      if (!analyserRef.current) return;

      const bufferLength = analyserRef.current.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);
      analyserRef.current.getByteFrequencyData(dataArray);

      // Normalize and map to waveform bars (60 bars)
      const normalizedData: number[] = [];
      const step = Math.floor(bufferLength / 60);
      
      for (let i = 0; i < 60; i++) {
        const index = i * step;
        const value = dataArray[index] || 0;
        // Normalize to 0-1 range
        normalizedData.push(Math.min(value / 255, 1));
      }

      setWaveformData(normalizedData);
      animationFrameRef.current = requestAnimationFrame(updateWaveform);
    };

    updateWaveform();

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      source.disconnect();
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, [stream, isActive]);

  return (
    <div className="flex items-center justify-center gap-[3px] h-16 w-full">
      {waveformData.map((value, index) => {
        const height = Math.max(value * 50, 3);
        const isBarActive = value > 0.05;
        
        return (
          <div
            key={index}
            className="rounded-full transition-all duration-100 ease-out"
            style={{
              width: '3px',
              height: `${height}px`,
              backgroundColor: isBarActive ? '#efc824' : '#374151',
            }}
          />
        );
      })}
    </div>
  );
};

export default AudioWaveform;
