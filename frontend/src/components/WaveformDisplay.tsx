/**
 * WaveformDisplay — Static waveform visualization only.
 * No independent playback. Clicking the play button loads
 * the track into the global sticky player via onPlay().
 */
import { useEffect, useRef, useState } from 'react';
import WaveSurfer from 'wavesurfer.js';
import { Play, Pause } from 'lucide-react';

interface WaveformDisplayProps {
  url: string;
  isPlaying: boolean;   // controlled by parent (sticky player state)
  onPlay: () => void;   // ask parent to start playing this track
  onPause: () => void;  // ask parent to pause
}

const WaveformDisplay = ({ url, isPlaying, onPlay, onPause }: WaveformDisplayProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WaveSurfer | null>(null);
  const [isReady, setIsReady] = useState(false);

  // Build the waveform shape — no audio, just visualization
  useEffect(() => {
    if (!containerRef.current) return;
    wsRef.current?.destroy();

    const ws = WaveSurfer.create({
      container: containerRef.current,
      waveColor: '#27272a',
      progressColor: '#2563eb',
      cursorColor: 'transparent',
      barWidth: 2,
      barGap: 1,
      barRadius: 2,
      height: 56,
      normalize: true,
      interact: false,   // no click-to-seek in this view
    });

    wsRef.current = ws;
    setIsReady(false);

    ws.load(url);
    ws.on('ready', () => setIsReady(true));

    return () => { ws.destroy(); };
  }, [url]);

  // Sync the visual progress bar with the sticky player
  // We use a very lightweight approach: just track isPlaying state visually
  // via the button — the actual waveform progress updates happen in StickyPlayer.

  const toggle = () => {
    if (isPlaying) onPause(); else onPlay();
  };

  return (
    <div className="flex items-center gap-3 bg-zinc-950/40 rounded-xl p-3 border border-zinc-800/40">
      <button
        onClick={toggle}
        disabled={!isReady}
        className="w-10 h-10 flex items-center justify-center rounded-full bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-md shrink-0"
      >
        {isPlaying
          ? <Pause size={15} fill="white" className="text-white" />
          : <Play size={15} fill="white" className="text-white ml-0.5" />
        }
      </button>
      <div className="flex-1 min-w-0" ref={containerRef} />
      {isPlaying && (
        <span className="text-xs text-blue-400 shrink-0 flex items-center gap-1">
          <span className="playing-bars-sm"><span /><span /><span /></span>
          playing
        </span>
      )}
    </div>
  );
};

export default WaveformDisplay;
