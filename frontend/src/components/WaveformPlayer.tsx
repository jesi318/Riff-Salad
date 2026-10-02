import { useEffect, useRef, useState } from 'react';
import WaveSurfer from 'wavesurfer.js';
import { Play, Pause } from 'lucide-react';

interface WaveformPlayerProps {
  url: string;
}

const WaveformPlayer = ({ url }: WaveformPlayerProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const wavesurferRef = useRef<WaveSurfer | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    if (!containerRef.current) return;

    const wavesurfer = WaveSurfer.create({
      container: containerRef.current,
      waveColor: '#52525b',
      progressColor: '#ffffff',
      cursorColor: '#ffffff',
      barWidth: 2,
      barGap: 1,
      barRadius: 2,
      height: 80,
    });

    wavesurferRef.current = wavesurfer;

    wavesurfer.load(url);

    wavesurfer.on('ready', () => {
      setIsReady(true);
    });

    wavesurfer.on('play', () => setIsPlaying(true));
    wavesurfer.on('pause', () => setIsPlaying(false));
    wavesurfer.on('finish', () => setIsPlaying(false));

    return () => {
      wavesurfer.destroy();
    };
  }, [url]);

  const togglePlay = () => {
    if (wavesurferRef.current) {
      wavesurferRef.current.playPause();
    }
  };

  return (
    <div className="flex items-center gap-4">
      <button 
        onClick={togglePlay} 
        disabled={!isReady}
        className="w-12 h-12 flex items-center justify-center rounded-full bg-white text-black hover:bg-zinc-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {isPlaying ? <Pause fill="currentColor" /> : <Play fill="currentColor" />}
      </button>
      <div className="flex-1" ref={containerRef} />
    </div>
  );
};

export default WaveformPlayer;
