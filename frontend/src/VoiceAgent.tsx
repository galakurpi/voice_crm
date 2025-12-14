import React, { useEffect, useRef, useState } from 'react';
import { floatTo16BitPCM, base64ToInt16Array } from './utils/audioUtils';
import { Button } from '@/components/ui/button';
import AudioWaveform from '@/components/AudioWaveform';
import ConversationView from '@/components/ConversationView';

interface Message {
  id: string;
  text: string;
  role: 'user' | 'assistant';
  timestamp: Date;
}

const VoiceAgent: React.FC = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [isMuted, setIsMuted] = useState(false);
  
  const socketRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const nextStartTimeRef = useRef(0);
  const scheduledAudioRef = useRef<AudioBufferSourceNode[]>([]);
  // Used to prevent races where async audio setup continues after the session is stopped/restarted.
  const sessionIdRef = useRef(0);

  useEffect(() => {
    return () => {
      stopSession();
    };
  }, []);

  const startSession = async () => {
    setIsMuted(false); // Reset mute state when starting new session
    
    // Use relative WebSocket URL that works with current protocol (ws/wss)
    const currentSessionId = ++sessionIdRef.current;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/voice-agent/`;
    console.log("[VoiceAgent] Connecting WebSocket:", wsUrl);
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;
    
    socket.onopen = () => {
      if (sessionIdRef.current !== currentSessionId) return;
      setIsConnected(true);
    };
    
    socket.onclose = () => {
        if (sessionIdRef.current !== currentSessionId) return;
        setIsConnected(false);
        stopAudio();
    };
    
    socket.onerror = (err) => {
        if (sessionIdRef.current !== currentSessionId) return;
        console.error("WebSocket Error", err);
        stopSession(socket);
    };
    
    socket.onmessage = async (event) => {
      // When testing with a simple echo WS server, messages may not be JSON.
      let data: any;
      try {
        data = JSON.parse(event.data);
      } catch {
        console.log("[VoiceAgent] WS message:", event.data);
        return;
      }
      
      // Handle server events
      if (data.type === 'response.audio.delta') {
          // Received audio chunk from OpenAI
          const audioData = base64ToInt16Array(data.delta);
          playAudioChunk(audioData);
      } else if (data.type === 'conversation.item.input_audio_transcription.completed') {
          // User speech transcription
          const transcript = data.transcript || '';
          if (transcript.trim()) {
              addMessage({
                  id: `user-${Date.now()}`,
                  text: transcript,
                  role: 'user',
                  timestamp: new Date(),
              });
          }
      } else if (data.type === 'response.audio_transcript.done') {
          // AI response transcription
          const transcript = data.transcript || '';
          if (transcript.trim()) {
              addMessage({
                  id: `assistant-${Date.now()}`,
                  text: transcript,
                  role: 'assistant',
                  timestamp: new Date(),
              });
          }
      } else if (data.type === 'response.function_call_arguments.done') {
          console.log("Tool Called:", data.name, data.arguments);
      } else if (data.type === 'input_audio_buffer.speech_started') {
          console.log("User started speaking - clearing audio queue");
          clearAudioQueue();
      } else if (data.type === 'error') {
          console.error("OpenAI Error:", data.error);
      }
    };

    // Start mic/audio immediately on click (user gesture), and only send once WS is open.
    startAudio(currentSessionId);
  };
  
  const startAudio = async (sessionId: number) => {
      try {
          // Initialize AudioContext at 24kHz (OpenAI Realtime default)
          const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({ 
              sampleRate: 24000 
          });
          audioContextRef.current = audioContext;
          nextStartTimeRef.current = audioContext.currentTime;

          await audioContext.audioWorklet.addModule('/audio-processor.js');
          if (sessionIdRef.current !== sessionId || audioContextRef.current !== audioContext) {
              // Session ended while we were awaiting the worklet module.
              try { await audioContext.close(); } catch {}
              if (audioContextRef.current === audioContext) audioContextRef.current = null;
              return;
          }
          
          const stream = await navigator.mediaDevices.getUserMedia({ 
              audio: { 
                  channelCount: 1, 
                  sampleRate: 24000,
                  echoCancellation: true,
                  noiseSuppression: true
              } 
          });
          if (sessionIdRef.current !== sessionId || audioContextRef.current !== audioContext) {
              // Session ended while the permission prompt was open.
              stream.getTracks().forEach(track => track.stop());
              try { await audioContext.close(); } catch {}
              if (audioContextRef.current === audioContext) audioContextRef.current = null;
              return;
          }
          streamRef.current = stream;
          setStream(stream);
          
          const source = audioContext.createMediaStreamSource(stream);
          const workletNode = new AudioWorkletNode(audioContext, 'audio-processor');
          
          workletNode.port.onmessage = (event) => {
              // Received Float32 audio from microphone
              // Convert to PCM16
              const pcm16 = floatTo16BitPCM(event.data);
              
              // Convert to Base64
              let binary = '';
              const bytes = new Uint8Array(pcm16.buffer);
              const len = bytes.byteLength;
              for (let i = 0; i < len; i++) {
                  binary += String.fromCharCode(bytes[i]);
              }
              const base64 = window.btoa(binary);
              
              // Send to backend
              if (socketRef.current?.readyState === WebSocket.OPEN) {
                  socketRef.current.send(JSON.stringify({
                      type: 'input_audio_buffer.append',
                      audio: base64
                  }));
              }
          };
          
          source.connect(workletNode);
          // Do NOT connect workletNode to destination to prevent local feedback loop
          
      } catch (err) {
          console.error("Audio Init Error", err);
          stopSession();
      }
  };
  
  const stopSession = (socketToClose?: WebSocket) => {
      // Invalidate in-flight async work (audio setup, stale socket handlers).
      sessionIdRef.current += 1;

      const socket = socketToClose ?? socketRef.current;
      if (socket) {
          try {
              socket.close();
          } catch {
              // Ignore close errors (e.g., already closed).
          }
      }
      if (!socketToClose || socketRef.current === socketToClose) {
          socketRef.current = null;
      }
      stopAudio();
      setIsMuted(false); // Reset mute state when stopping session
      // Optionally clear messages on stop, or keep them for history
      // setMessages([]);
  };
  
  const addMessage = (message: Message) => {
      setMessages(prev => [...prev, message]);
  };

  const stopAudio = () => {
      clearAudioQueue();
      if (streamRef.current) {
          streamRef.current.getTracks().forEach(track => track.stop());
          streamRef.current = null;
      }
      setStream(null);
      if (audioContextRef.current) {
          audioContextRef.current.close();
          audioContextRef.current = null;
      }
      setIsConnected(false);
  };
  
  const clearAudioQueue = () => {
      scheduledAudioRef.current.forEach(source => {
          try {
              source.stop();
          } catch (e) {
              // Ignore errors if already stopped
          }
      });
      scheduledAudioRef.current = [];
      if (audioContextRef.current) {
          nextStartTimeRef.current = audioContextRef.current.currentTime;
      }
  };

  const toggleMute = () => {
      if (streamRef.current) {
          const audioTracks = streamRef.current.getAudioTracks();
          const newMutedState = !isMuted;
          audioTracks.forEach(track => {
              track.enabled = !newMutedState;
          });
          setIsMuted(newMutedState);
      }
  };

  const playAudioChunk = (pcmData: Int16Array) => {
      if (!audioContextRef.current) return;
      
      const audioCtx = audioContextRef.current;
      // Convert Int16 -> Float32 for playback
      const float32 = new Float32Array(pcmData.length);
      for(let i=0; i<pcmData.length; i++) {
          float32[i] = pcmData[i] / 0x8000;
      }
      
      const buffer = audioCtx.createBuffer(1, float32.length, 24000);
      buffer.copyToChannel(float32, 0);
      
      const source = audioCtx.createBufferSource();
      source.buffer = buffer;
      source.connect(audioCtx.destination);
      
      // Schedule playback to ensure smooth audio
      const currentTime = audioCtx.currentTime;
      // If we fell behind, reset to current time
      const startTime = Math.max(currentTime, nextStartTimeRef.current);
      
      source.onended = () => {
          scheduledAudioRef.current = scheduledAudioRef.current.filter(s => s !== source);
      };
      
      source.start(startTime);
      nextStartTimeRef.current = startTime + buffer.duration;
      scheduledAudioRef.current.push(source);
  };

  return (
    <div className="min-h-screen bg-[#212121] flex flex-col">
      {/* Header */}
      <header className="flex items-center px-6 py-4 border-b border-[#333]">
        <h1 className="text-white text-lg font-medium">
          Voice CRM <span className="text-gray-400 font-normal">Agent</span>
        </h1>
      </header>
      
      {/* Main Chat Area */}
      <main className="flex-1 overflow-hidden flex flex-col">
        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="max-w-3xl mx-auto">
            <ConversationView messages={messages} />
          </div>
        </div>
      </main>
      
      {/* Bottom Controls */}
      <footer className="border-t border-[#333] bg-[#212121]">
        <div className="max-w-3xl mx-auto px-4 py-4">
          {/* Waveform - only show when connected */}
          {isConnected && (
            <div className="mb-4 flex justify-center">
              <div className="w-64">
                <AudioWaveform 
                  stream={stream}
                  isActive={isConnected}
                />
              </div>
            </div>
          )}
          
          {/* Input Area Style */}
          <div className="bg-[#2f2f2f] rounded-2xl px-4 py-3 flex items-center gap-3">
            <span className="text-gray-500 text-sm flex-1">
              {isConnected ? 'Listening...' : 'Click to start voice conversation'}
            </span>
            
            {/* Mic Icon */}
            <button 
              onClick={toggleMute}
              disabled={!isConnected}
              className={`p-2 transition-colors ${
                isMuted 
                  ? 'text-red-500 hover:text-red-400' 
                  : isConnected 
                    ? 'text-gray-400 hover:text-[#efc824]' 
                    : 'text-gray-400 opacity-50 cursor-not-allowed'
              }`}
            >
              {isMuted ? (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                    d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" 
                  />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                    d="M5 5l14 14" 
                  />
                </svg>
              ) : (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                    d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" 
                  />
                </svg>
              )}
            </button>
            
            {/* Start/End Button */}
            <Button 
              onClick={isConnected ? () => stopSession() : startSession}
              className={`h-9 px-4 rounded-xl text-sm font-medium transition-all ${
                isConnected 
                  ? 'bg-[#444] hover:bg-[#555] text-gray-200' 
                  : 'bg-[#efc824] hover:bg-[#d4b01f] text-black'
              }`}
            >
              {isConnected ? '●●●● End' : 'Start'}
            </Button>
          </div>
          
          <p className="text-center text-xs text-gray-500 mt-3">
            Voice CRM Agent can make mistakes. Check important info.
          </p>
        </div>
      </footer>
    </div>
  );
};

export default VoiceAgent;

