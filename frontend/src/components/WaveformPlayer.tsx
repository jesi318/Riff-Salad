import { useEffect, useRef, useState, useCallback } from 'react';
import WaveSurfer from 'wavesurfer.js';
import { Play, Pause } from 'lucide-react';

interface WaveformPlayerProps {
  url: string;
  onPlay?: () => void;
  isGlobalPlaying?: boolean;
}

const WaveformPlayer = ({ url, onPlay, isGlobalPlaying }: WaveformPlayerProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const wavesurferRef = useRef<WaveSurfer | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  useEffect(() => {
    if (!containerRef.current) return;

    wavesurferRef.current?.destroy();

    const wavesurfer = WaveSurfer.create({
      container: containerRef.current,
      waveColor: '#3f3f46',
      progressColor: '#7c3aed',
      cursorColor: '#a78bfa',
      barWidth: 2,
      barGap: 1,
      barRadius: 2,
      height: 64,
      normalize: true,
    });

    wavesurferRef.current = wavesurfer;
    setIsReady(false);
    setIsPlaying(false);

    wavesurfer.load(url);

    wavesurfer.on('ready', () => {
      setIsReady(true);
      setDuration(wavesurfer.getDuration());
    });

    wavesurfer.on('play', () => setIsPlaying(true));
    wavesurfer.on('pause', () => setIsPlaying(false));
    wavesurfer.on('finish', () => setIsPlaying(false));
    wavesurfer.on('timeupdate', t => setCurrentTime(t));

    return () => { wavesurfer.destroy(); };
  }, [url]);

  const togglePlay = useCallback(() => {
    if (!wavesurferRef.current) return;
    wavesurferRef.current.playPause();
    if (!isPlaying) onPlay?.();
  }, [isPlaying, onPlay]);

  const fmt = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, '0')}`;
  };

  return (
    <div className="flex items-center gap-3 bg-zinc-950/60 rounded-xl p-3">
      <button
        onClick={togglePlay}
        disabled={!isReady}
        className="w-10 h-10 flex items-center justify-center rounded-full bg-violet-600 hover:bg-violet-500 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-md shrink-0"
      >
        {isPlaying
          ? <Pause size={15} fill="white" className="text-white" />
          : <Play size={15} fill="white" className="text-white ml-0.5" />
        }
      </button>

      <div className="flex-1 min-w-0 flex flex-col gap-1">
        <div ref={containerRef} />
        {isReady && (
          <div className="flex justify-between text-xs text-zinc-600 tabular-nums px-0.5">
            <span>{fmt(currentTime)}</span>
            <span>{fmt(duration)}</span>
          </div>
        )}
      </div>

      {isGlobalPlaying && (
        <span className="text-xs text-violet-400 shrink-0 flex items-center gap-1">
          <span className="playing-bars-sm"><span/><span/><span/></span>
          playing
        </span>
      )}
    </div>
  );
};

export default WaveformPlayer;
