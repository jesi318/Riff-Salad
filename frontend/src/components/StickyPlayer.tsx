import { useEffect, useRef, useState, useCallback } from 'react';
import WaveSurfer from 'wavesurfer.js';
import { Play, Pause, X, Music } from 'lucide-react';

interface StickyPlayerProps {
  riff: { id: number; title: string; bpm: number | null; key: string | null } | null;
  audioUrl: string | null;
  isPlaying: boolean;           // external truth (from parent)
  onClose: () => void;
  onPlay: () => void;           // tell parent we started playing
  onPause: () => void;          // tell parent we paused
  externalToggle?: number;      // increment to toggle via spacebar
}

const StickyPlayer = ({
  riff, audioUrl, isPlaying, onClose, onPlay, onPause, externalToggle,
}: StickyPlayerProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const wavesurferRef = useRef<WaveSurfer | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const prevToggle = useRef(externalToggle);
  const prevUrl = useRef<string | null>(null);

  // Build/rebuild wavesurfer when URL changes
  useEffect(() => {
    if (!containerRef.current || !audioUrl) return;
    if (audioUrl === prevUrl.current) return;   // same track, don't reload
    prevUrl.current = audioUrl;

    wavesurferRef.current?.destroy();

    const ws = WaveSurfer.create({
      container: containerRef.current,
      waveColor: 'rgba(99,102,241,0.25)',
      progressColor: '#3b82f6',
      cursorColor: '#60a5fa',
      barWidth: 2,
      barGap: 1,
      barRadius: 2,
      height: 36,
      normalize: true,
    });

    wavesurferRef.current = ws;
    setIsReady(false);
    setCurrentTime(0);
    setDuration(0);

    ws.load(audioUrl);

    ws.on('ready', () => {
      setIsReady(true);
      setDuration(ws.getDuration());
      ws.play();
      onPlay();
    });

    ws.on('play', onPlay);
    ws.on('pause', onPause);
    ws.on('finish', onPause);
    ws.on('timeupdate', t => setCurrentTime(t));

    return () => { ws.destroy(); prevUrl.current = null; };
  }, [audioUrl]);

  // Sync external play/pause from parent (e.g. from WaveformDisplay button)
  useEffect(() => {
    if (!wavesurferRef.current || !isReady) return;
    const ws = wavesurferRef.current;
    if (isPlaying && !ws.isPlaying()) ws.play();
    if (!isPlaying && ws.isPlaying()) ws.pause();
  }, [isPlaying, isReady]);

  // Spacebar toggle
  useEffect(() => {
    if (externalToggle === prevToggle.current) return;
    prevToggle.current = externalToggle;
    if (wavesurferRef.current && isReady) {
      if (wavesurferRef.current.isPlaying()) { wavesurferRef.current.pause(); onPause(); }
      else { wavesurferRef.current.play(); onPlay(); }
    }
  }, [externalToggle, isReady]);

  const togglePlay = useCallback(() => {
    if (!wavesurferRef.current) return;
    if (wavesurferRef.current.isPlaying()) { wavesurferRef.current.pause(); onPause(); }
    else { wavesurferRef.current.play(); onPlay(); }
  }, [onPlay, onPause]);

  const fmt = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, '0')}`;
  };

  if (!riff || !audioUrl) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 bg-zinc-950/96 backdrop-blur-md border-t border-zinc-800/80">
      <div className="max-w-7xl mx-auto px-8 py-2.5 flex items-center gap-4">
        {/* Track info */}
        <div className="flex items-center gap-2.5 w-52 shrink-0 min-w-0">
          <div className="w-8 h-8 rounded-md bg-blue-900/40 flex items-center justify-center shrink-0">
            <Music size={14} className="text-blue-400" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium text-white truncate leading-tight">{riff.title}</p>
            <p className="text-xs text-zinc-500 truncate">
              {[riff.bpm ? `${Math.round(riff.bpm)} BPM` : null, riff.key].filter(Boolean).join(' · ')}
            </p>
          </div>
        </div>

        {/* Controls */}
        <button
          onClick={togglePlay}
          disabled={!isReady}
          className="w-8 h-8 rounded-full flex items-center justify-center bg-blue-600 hover:bg-blue-500 transition-all disabled:opacity-40 shrink-0"
        >
          {isPlaying
            ? <Pause size={13} fill="white" className="text-white" />
            : <Play size={13} fill="white" className="text-white ml-px" />
          }
        </button>

        {/* Time */}
        <span className="text-xs text-zinc-600 tabular-nums shrink-0 w-16 text-center">
          {fmt(currentTime)} / {fmt(duration)}
        </span>

        {/* Waveform */}
        <div className="flex-1 min-w-0" ref={containerRef} />

        {/* Spacebar hint */}
        <span className="text-xs text-zinc-700 shrink-0 hidden lg:block">Space to play/pause</span>

        {/* Close */}
        <button
          onClick={onClose}
          className="p-1.5 text-zinc-600 hover:text-white hover:bg-zinc-800 rounded-md transition-colors shrink-0"
        >
          <X size={14} />
        </button>
      </div>
    </div>
  );
};

export default StickyPlayer;
