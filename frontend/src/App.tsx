import { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { Toaster, toast } from 'react-hot-toast';
import {
  Upload, FileAudio, Search, RefreshCw, Trash2, RotateCcw,
  Mic, Sparkles, ListMusic, X, Check, Pencil
} from 'lucide-react';
import WaveformDisplay from './components/WaveformDisplay';
import VoiceRecorder from './components/VoiceRecorder';
import StickyPlayer from './components/StickyPlayer';
import SkeletonCard from './components/SkeletonCard';

const API = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000/api';
const RIFFS_URL = `${API}/riffs`;

type Riff = {
  id: number;
  title: string;
  filename: string;
  filepath: string;
  created_at: string;
  analysis_status: string;
  analysis_progress: number;
  bpm: number | null;
  key: string | null;
  duration: number | null;
  energy: number | null;
  onset_density: number | null;
  midi_filepath: string | null;
  voice_note_transcript: string | null;
  user_notes: string | null;
  tags: string | null;
  ai_description: string | null;
  embedding_path: string | null;
};

type SearchResult = { riff: Riff; score: number | null; match_type: string };
type SimilarResult = { riff: Riff; similarity: number };

function parseTags(raw: string | null): string[] {
  if (!raw) return [];
  try { return JSON.parse(raw); } catch { return []; }
}

// ── Inline editable title ────────────────────────────────────────────────────
function InlineTitle({ riffId, value, onSaved }: { riffId: number; value: string; onSaved: (v: string) => void }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { if (editing) inputRef.current?.select(); }, [editing]);
  useEffect(() => { setDraft(value); }, [value]);

  const save = async () => {
    if (draft.trim() === value) { setEditing(false); return; }
    try {
      await axios.patch(`${RIFFS_URL}/${riffId}/title`, { title: draft.trim() });
      onSaved(draft.trim());
      toast.success('Title updated');
    } catch {
      toast.error('Failed to update title');
      setDraft(value);
    }
    setEditing(false);
  };

  if (editing) {
    return (
      <div className="flex items-center gap-2">
        <input
          ref={inputRef}
          value={draft}
          onChange={e => setDraft(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') save(); if (e.key === 'Escape') { setDraft(value); setEditing(false); } }}
          className="bg-zinc-800 border border-blue-500/50 rounded-lg px-3 py-1 text-xl font-bold focus:outline-none transition-colors flex-1"
        />
        <button onClick={save} className="p-1.5 text-green-400 hover:bg-zinc-800 rounded transition-colors"><Check size={15} /></button>
        <button onClick={() => { setDraft(value); setEditing(false); }} className="p-1.5 text-zinc-500 hover:text-white hover:bg-zinc-800 rounded transition-colors"><X size={15} /></button>
      </div>
    );
  }

  return (
    <button onClick={() => setEditing(true)} className="group flex items-center gap-2 text-left" title="Click to rename">
      <h2 className="text-2xl font-bold leading-tight group-hover:text-blue-300 transition-colors">{value}</h2>
      <Pencil size={13} className="text-zinc-700 group-hover:text-blue-400 transition-colors opacity-0 group-hover:opacity-100 shrink-0" />
    </button>
  );
}

// ── Inline editable meta field ───────────────────────────────────────────────
function InlineMetaField({ label, value, riffId, field, onSaved }: {
  label: string; value: string | number | null; riffId: number; field: string; onSaved: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(String(value ?? ''));

  const save = async () => {
    try {
      await axios.patch(`${RIFFS_URL}/${riffId}/meta`, { [field]: draft });
      onSaved();
      toast.success(`${label} updated`);
    } catch {
      toast.error(`Failed to update ${label}`);
    }
    setEditing(false);
  };

  if (editing) {
    return (
      <div className="bg-zinc-950 p-3 rounded-lg border border-blue-500/40">
        <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-1">{label}</p>
        <input
          autoFocus
          value={draft}
          onChange={e => setDraft(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') save(); if (e.key === 'Escape') setEditing(false); }}
          onBlur={save}
          className="w-full bg-transparent text-sm font-medium focus:outline-none tabular-nums"
        />
      </div>
    );
  }

  return (
    <button
      onClick={() => { setDraft(String(value ?? '')); setEditing(true); }}
      className="bg-zinc-950 p-3 rounded-lg border border-zinc-800/60 hover:border-zinc-700 transition-colors text-left group w-full"
      title={`Click to edit ${label}`}
    >
      <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-1">{label}</p>
      <p className="text-sm font-medium tabular-nums">{value ?? '--'}</p>
    </button>
  );
}

// ── Processing stage label ────────────────────────────────────────────────────
function getProcessingLabel(progress: number): string {
  if (progress < 0.3) return 'Loading audio…';
  if (progress < 0.6) return 'Analyzing BPM & Key…';
  if (progress < 0.8) return 'Extracting features…';
  if (progress < 0.95) return 'Running AI tagging…';
  return 'Finalizing…';
}

// ── Drag overlay ──────────────────────────────────────────────────────────────
function DragOverlay({ active }: { active: boolean }) {
  if (!active) return null;
  return (
    <div className="fixed inset-0 z-40 bg-zinc-950/85 backdrop-blur-sm flex items-center justify-center pointer-events-none">
      <div className="border-2 border-dashed border-blue-500/60 rounded-2xl p-16 flex flex-col items-center gap-4">
        <Upload size={40} className="text-blue-400 animate-bounce" />
        <p className="text-lg font-semibold text-zinc-200">Drop your riff here</p>
        <p className="text-sm text-zinc-500">WAV, MP3, or M4A</p>
      </div>
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [riffs, setRiffs] = useState<Riff[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedRiff, setSelectedRiff] = useState<Riff | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [similarResults, setSimilarResults] = useState<SimilarResult[] | null>(null);
  const [loadingSimilar, setLoadingSimilar] = useState(false);
  const [editingNotes, setEditingNotes] = useState(false);
  const [notesValue, setNotesValue] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [newRiffId, setNewRiffId] = useState<number | null>(null);

  // Single player state — the ONE source of truth for playback
  const [playerRiff, setPlayerRiff] = useState<Riff | null>(null);
  const [playerUrl, setPlayerUrl] = useState<string | null>(null);
  const [globalIsPlaying, setGlobalIsPlaying] = useState(false);
  const [spacebarToggle, setSpacebarToggle] = useState(0);

  const voiceInputRef = useRef<HTMLInputElement>(null);
  const searchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dragCounterRef = useRef(0);

  // ── Polling ────────────────────────────────────────────────────────────────
  useEffect(() => {
    fetchRiffs(true);
    const id = setInterval(() => fetchRiffs(false), 3000);
    return () => clearInterval(id);
  }, []);

  const fetchRiffs = async (initial = false) => {
    try {
      const { data } = await axios.get<Riff[]>(RIFFS_URL);
      if (initial) setLoading(false);
      setRiffs(data);
      setSelectedRiff(cur => cur ? (data.find(r => r.id === cur.id) ?? cur) : null);
      setPlayerRiff(cur => cur ? (data.find(r => r.id === cur.id) ?? cur) : null);
    } catch {
      if (initial) setLoading(false);
    }
  };

  // ── Global spacebar shortcut ───────────────────────────────────────────────
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (['INPUT', 'TEXTAREA'].includes(target.tagName) || target.isContentEditable) return;
      if (e.code === 'Space' && playerUrl) {
        e.preventDefault();
        setSpacebarToggle(n => n + 1);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [playerUrl]);

  // ── Drag & Drop ───────────────────────────────────────────────────────────
  useEffect(() => {
    const onDragEnter = (e: DragEvent) => {
      e.preventDefault();
      dragCounterRef.current++;
      if (e.dataTransfer?.types.includes('Files')) setIsDragging(true);
    };
    const onDragLeave = () => {
      dragCounterRef.current--;
      if (dragCounterRef.current <= 0) { dragCounterRef.current = 0; setIsDragging(false); }
    };
    const onDragOver = (e: DragEvent) => e.preventDefault();
    const onDrop = async (e: DragEvent) => {
      e.preventDefault();
      dragCounterRef.current = 0; setIsDragging(false);
      const files = Array.from(e.dataTransfer?.files ?? []).filter(f => /\.(wav|mp3|m4a)$/i.test(f.name));
      if (!files.length) { toast.error('Only WAV, MP3, or M4A files are supported'); return; }
      for (const file of files) await uploadFile(file);
    };
    document.addEventListener('dragenter', onDragEnter);
    document.addEventListener('dragleave', onDragLeave);
    document.addEventListener('dragover', onDragOver);
    document.addEventListener('drop', onDrop);
    return () => {
      document.removeEventListener('dragenter', onDragEnter);
      document.removeEventListener('dragleave', onDragLeave);
      document.removeEventListener('dragover', onDragOver);
      document.removeEventListener('drop', onDrop);
    };
  }, []);

  // ── Upload ────────────────────────────────────────────────────────────────
  const uploadFile = async (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!ext || !['wav', 'mp3', 'm4a'].includes(ext)) {
      toast.error(`Unsupported format: .${ext}`); return;
    }
    const t = toast.loading(`Uploading "${file.name}"…`);
    try {
      const fd = new FormData(); fd.append('file', file);
      const { data } = await axios.post<Riff>(RIFFS_URL, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      toast.success(`"${data.title}" uploaded! Analyzing…`, { id: t });
      setNewRiffId(data.id);
      setTimeout(() => setNewRiffId(null), 4000);
      fetchRiffs();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Upload failed', { id: t });
    }
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]; if (!file) return;
    await uploadFile(file); e.target.value = '';
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this riff?')) return;
    try {
      await axios.delete(`${RIFFS_URL}/${id}`);
      if (playerRiff?.id === id) { setPlayerRiff(null); setPlayerUrl(null); setGlobalIsPlaying(false); }
      setSelectedRiff(null); setSimilarResults(null);
      fetchRiffs(); toast.success('Riff deleted');
    } catch { toast.error('Failed to delete'); }
  };

  const handleReanalyze = async (id: number) => {
    try {
      await axios.post(`${RIFFS_URL}/${id}/analyze`);
      fetchRiffs(); toast('Re-analyzing…', { icon: '🔄' });
    } catch { toast.error('Failed to start re-analysis'); }
  };

  // ── Search ────────────────────────────────────────────────────────────────
  const runSearch = useCallback(async (q: string) => {
    if (!q.trim()) { setSearchResults(null); return; }
    setSearching(true);
    try {
      const { data } = await axios.get<SearchResult[]>(`${API}/search`, { params: { q } });
      setSearchResults(data);
    } catch { toast.error('Search failed'); }
    finally { setSearching(false); }
  }, []);

  const handleSearchInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const q = e.target.value; setSearchQuery(q);
    if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
    searchDebounceRef.current = setTimeout(() => runSearch(q), 500);
  };

  const clearSearch = () => {
    setSearchQuery(''); setSearchResults(null);
    if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
  };

  const handleFindSimilar = async (id: number) => {
    setLoadingSimilar(true); setSimilarResults(null);
    try {
      const { data } = await axios.get<SimilarResult[]>(`${RIFFS_URL}/${id}/similar`);
      setSimilarResults(data);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Could not find similar riffs.');
    } finally { setLoadingSimilar(false); }
  };

  const handleVoiceNote = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]; if (!file || !selectedRiff) return;
    const fd = new FormData(); fd.append('file', file);
    const t = toast.loading('Transcribing voice note…');
    try {
      await axios.post(`${RIFFS_URL}/${selectedRiff.id}/transcribe`, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      toast.success('Voice note transcribed!', { id: t }); fetchRiffs();
    } catch { toast.error('Transcription failed', { id: t }); }
    e.target.value = '';
  };

  const handleSaveNotes = async () => {
    if (!selectedRiff) return;
    try {
      await axios.patch(`${RIFFS_URL}/${selectedRiff.id}/notes`, { user_notes: notesValue });
      setEditingNotes(false); fetchRiffs(); toast.success('Notes saved');
    } catch { toast.error('Failed to save notes'); }
  };

  // ── Player helpers ────────────────────────────────────────────────────────
  const loadTrack = (riff: Riff) => {
    const url = `${RIFFS_URL}/${riff.id}/audio`;
    if (playerUrl === url) {
      // Same track — just toggle
      setGlobalIsPlaying(p => !p);
    } else {
      // New track — StickyPlayer will auto-play on load
      setPlayerRiff(riff);
      setPlayerUrl(url);
    }
  };

  const handleTitleSaved = (newTitle: string) => {
    setSelectedRiff(r => r ? { ...r, title: newTitle } : r);
    setRiffs(rs => rs.map(r => r.id === selectedRiff?.id ? { ...r, title: newTitle } : r));
  };

  // ── Derived ───────────────────────────────────────────────────────────────
  const listRiffs = searchResults ? searchResults.map(r => r.riff) : riffs;
  const currentUrl = selectedRiff ? `${RIFFS_URL}/${selectedRiff.id}/audio` : null;
  const detailIsPlaying = globalIsPlaying && playerUrl === currentUrl;

  return (
    <div className="min-h-screen pb-20">
      <Toaster
        position="top-right"
        toastOptions={{
          style: { background: '#18181b', color: '#f4f4f5', border: '1px solid #27272a', fontSize: '13px' },
          success: { iconTheme: { primary: '#3b82f6', secondary: '#18181b' } },
        }}
      />

      <DragOverlay active={isDragging} />

      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <header className="border-b border-zinc-800/50 bg-zinc-950/80 backdrop-blur sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-8 py-4 flex justify-between items-center">
          <div className="editor-canvas">
            <h1 className="playwrite-heading">Riff Salad</h1>
          </div>
          <div className="flex gap-2 items-center">
            <button
              onClick={() => fetchRiffs()}
              className="p-2 text-zinc-600 hover:text-white hover:bg-zinc-800/60 rounded-lg transition-colors"
              title="Refresh"
            >
              <RefreshCw size={15} />
            </button>
            <label className="cursor-pointer bg-blue-600 hover:bg-blue-500 px-4 py-2 rounded-lg flex items-center gap-2 text-sm font-medium transition-all">
              <Upload size={14} /> Import Riff
              <input type="file" className="hidden" accept=".wav,.mp3,.m4a" onChange={handleImport} />
            </label>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-8 py-8">
        {/* ── Search ──────────────────────────────────────────────────────── */}
        <div className="mb-6 relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-600" size={16} />
          <input
            type="text"
            value={searchQuery}
            onChange={handleSearchInput}
            placeholder='Search your riffs… "heavy Drop C riffs around 140 BPM"'
            className="w-full bg-zinc-900/60 border border-zinc-800/80 rounded-xl pl-10 pr-10 py-3 text-sm focus:outline-none focus:border-blue-500/40 focus:bg-zinc-900 transition-all placeholder:text-zinc-600"
          />
          {(searching || searchQuery) && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 flex gap-2 items-center">
              {searching
                ? <span className="text-xs text-zinc-500 animate-pulse">Searching…</span>
                : <button onClick={clearSearch} className="text-zinc-500 hover:text-white transition-colors p-0.5"><X size={13} /></button>
              }
            </div>
          )}
        </div>

        {/* Search summary */}
        {searchResults !== null && (
          <div className="flex items-center gap-3 mb-5 flex-wrap">
            <p className="text-zinc-600 text-xs">
              {searchResults.length} result{searchResults.length !== 1 ? 's' : ''} for
              <span className="text-zinc-400 ml-1">"{searchQuery}"</span>
            </p>
            <button
              onClick={clearSearch}
              className="flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
            >
              <X size={10} /> Clear
            </button>
          </div>
        )}

        <div className="grid grid-cols-3 gap-8">
          {/* ── Sidebar ───────────────────────────────────────────────────── */}
          <div className="col-span-1">
            <div className="flex flex-col gap-0.5">
              {loading ? (
                Array.from({ length: 5 }).map((_, i) => <SkeletonCard key={i} />)
              ) : searching ? (
                Array.from({ length: 3 }).map((_, i) => <SkeletonCard key={i} />)
              ) : listRiffs.length === 0 ? (
                <div className="flex flex-col items-center text-center mt-16 px-4 gap-3">
                  <FileAudio size={32} className="text-zinc-700" />
                  {searchResults !== null ? (
                    <>
                      <p className="text-sm text-zinc-500">No riffs found for "{searchQuery}"</p>
                      <button onClick={clearSearch} className="text-xs text-blue-400 hover:text-blue-300 transition-colors">Clear search</button>
                    </>
                  ) : (
                    <p className="text-sm text-zinc-600">Your vault is empty.<br />Import a riff or drag & drop an audio file.</p>
                  )}
                </div>
              ) : (
                listRiffs.map(riff => {
                  const sr = searchResults?.find(r => r.riff.id === riff.id);
                  const isSelected = selectedRiff?.id === riff.id;
                  const isActiveTrack = playerRiff?.id === riff.id;
                  const isNew = riff.id === newRiffId;

                  return (
                    <div
                      key={riff.id}
                      onClick={() => { setSelectedRiff(riff); setSimilarResults(null); }}
                      className={`
                        riff-card px-3 py-2.5 rounded-lg cursor-pointer transition-all
                        ${isSelected ? 'bg-zinc-800/60' : 'hover:bg-zinc-900/50'}
                        ${isNew ? 'ring-1 ring-blue-500/30' : ''}
                      `}
                    >
                      <div className="flex items-center gap-2.5">
                        <div className={`shrink-0 w-6 h-6 rounded flex items-center justify-center transition-colors ${isActiveTrack ? 'bg-blue-600' : 'bg-zinc-800'
                          }`}>
                          {isActiveTrack && globalIsPlaying
                            ? <span className="playing-bars"><span /><span /><span /></span>
                            : <FileAudio size={12} className={isSelected ? 'text-zinc-400' : 'text-zinc-600'} />
                          }
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className={`text-sm truncate ${isSelected ? 'text-white font-medium' : 'text-zinc-400'}`} title={riff.title}>
                            {riff.title}
                          </p>
                          <div className="flex gap-2 mt-0.5 items-center flex-wrap">
                            {riff.bpm && <span className="text-xs text-zinc-600 tabular-nums">{Math.round(riff.bpm)} BPM</span>}
                            {riff.key && <span className="text-xs text-zinc-700">{riff.key}</span>}
                            {sr?.score != null && <span className="text-xs text-blue-400 font-medium">{Math.round(sr.score * 100)}%</span>}
                            {riff.analysis_status === 'processing' && (
                              <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse inline-block" />
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* ── Detail panel ──────────────────────────────────────────────── */}
          <div className="col-span-2">
            {selectedRiff ? (
              <div className="space-y-5">
                {/* Title + actions */}
                <div className="flex justify-between items-start gap-4">
                  <div className="flex-1 min-w-0">
                    <InlineTitle riffId={selectedRiff.id} value={selectedRiff.title} onSaved={handleTitleSaved} />
                    <p className="text-zinc-600 text-xs mt-1">{new Date(selectedRiff.created_at).toLocaleString()}</p>
                  </div>
                  <div className="flex gap-1 shrink-0">
                    <button
                      onClick={() => handleReanalyze(selectedRiff.id)}
                      disabled={selectedRiff.analysis_status === 'processing'}
                      className="p-2 text-zinc-600 hover:text-white hover:bg-zinc-800/60 rounded-lg transition-colors disabled:opacity-40 flex items-center gap-1.5 text-xs"
                      title="Re-analyze audio + regenerate AI tags"
                    >
                      <RotateCcw size={14} />
                      <span>Re-analyze</span>
                    </button>
                    <button onClick={() => handleDelete(selectedRiff.id)} className="p-2 text-zinc-600 hover:text-red-400 hover:bg-zinc-800/60 rounded-lg transition-colors" title="Delete">
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>

                {/* Waveform — controlled by global player */}
                <WaveformDisplay
                  url={`${RIFFS_URL}/${selectedRiff.id}/audio`}
                  isPlaying={detailIsPlaying}
                  onPlay={() => loadTrack(selectedRiff)}
                  onPause={() => setGlobalIsPlaying(false)}
                />

                {/* Processing progress */}
                {selectedRiff.analysis_status === 'processing' && (
                  <div className="bg-zinc-900/60 border border-zinc-800/40 rounded-lg p-3">
                    <div className="flex justify-between text-xs text-zinc-500 mb-2">
                      <span className="flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse inline-block" />
                        {getProcessingLabel(selectedRiff.analysis_progress || 0)}
                      </span>
                      <span className="tabular-nums">{Math.round((selectedRiff.analysis_progress || 0) * 100)}%</span>
                    </div>
                    <div className="w-full bg-zinc-800 rounded-full h-0.5">
                      <div
                        className="bg-amber-500 h-0.5 rounded-full transition-all duration-700"
                        style={{ width: `${(selectedRiff.analysis_progress || 0) * 100}%` }}
                      />
                    </div>
                  </div>
                )}

                {/* Metadata grid */}
                <div className="grid grid-cols-4 gap-2">
                  <div className="bg-zinc-950/60 p-3 rounded-lg border border-zinc-800/40">
                    <p className="text-xs text-zinc-600 uppercase tracking-wider mb-1">Status</p>
                    <p className={`text-sm font-medium capitalize ${selectedRiff.analysis_status === 'completed' ? 'text-green-400' :
                        selectedRiff.analysis_status === 'failed' ? 'text-red-400' : 'text-amber-400'
                      }`}>{selectedRiff.analysis_status}</p>
                  </div>
                  <InlineMetaField label="BPM" value={selectedRiff.bpm ? Math.round(selectedRiff.bpm) : null} riffId={selectedRiff.id} field="bpm" onSaved={() => fetchRiffs()} />
                  <InlineMetaField label="Key" value={selectedRiff.key} riffId={selectedRiff.id} field="key" onSaved={() => fetchRiffs()} />
                  <div className="bg-zinc-950/60 p-3 rounded-lg border border-zinc-800/40">
                    <p className="text-xs text-zinc-600 uppercase tracking-wider mb-1">Duration</p>
                    <p className="text-sm font-medium tabular-nums">{selectedRiff.duration ? `${selectedRiff.duration.toFixed(1)}s` : '--'}</p>
                  </div>
                </div>

                {/* AI description */}
                {selectedRiff.ai_description && (
                  <div className="bg-zinc-950/40 border border-zinc-800/40 rounded-lg p-4">
                    <p className="text-xs text-zinc-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                      <Sparkles size={11} /> AI Description
                      <span className="text-zinc-700 font-normal normal-case">(estimated)</span>
                    </p>
                    <p className="text-sm text-zinc-300 leading-relaxed">{selectedRiff.ai_description}</p>
                  </div>
                )}

                {/* Tags */}
                {parseTags(selectedRiff.tags).length > 0 && (
                  <div>
                    <p className="text-xs text-zinc-600 uppercase tracking-wider mb-2">Tags</p>
                    <div className="flex flex-wrap gap-1.5">
                      {parseTags(selectedRiff.tags).map(tag => (
                        <span key={tag} className="bg-zinc-800/60 text-zinc-400 text-xs px-2.5 py-1 rounded-full">{tag}</span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Voice note */}
                <div className="bg-zinc-950/40 border border-zinc-800/40 rounded-lg p-4">
                  <div className="flex justify-between items-center mb-2">
                    <p className="text-xs text-zinc-600 uppercase tracking-wider flex items-center gap-1.5"><Mic size={11} /> Voice Note</p>
                    <div className="flex items-center gap-3">
                      <VoiceRecorder riffId={selectedRiff.id} onUploadComplete={fetchRiffs} />
                      <label className="cursor-pointer text-xs text-zinc-600 hover:text-white transition-colors flex items-center gap-1 border-l border-zinc-800 pl-3">
                        <Upload size={11} /> Upload
                        <input ref={voiceInputRef} type="file" className="hidden" accept=".wav,.mp3,.m4a,.ogg" onChange={handleVoiceNote} />
                      </label>
                    </div>
                  </div>
                  {selectedRiff.voice_note_transcript
                    ? <p className="text-sm text-zinc-300 italic leading-relaxed">"{selectedRiff.voice_note_transcript}"</p>
                    : <p className="text-sm text-zinc-600">No voice note yet. Record or upload an audio note.</p>
                  }
                </div>

                {/* User notes */}
                <div className="bg-zinc-950/40 border border-zinc-800/40 rounded-lg p-4">
                  <div className="flex justify-between items-center mb-2">
                    <p className="text-xs text-zinc-600 uppercase tracking-wider">Notes</p>
                    {!editingNotes && (
                      <button onClick={() => { setEditingNotes(true); setNotesValue(selectedRiff.user_notes || ''); }}
                        className="text-xs text-zinc-600 hover:text-white transition-colors flex items-center gap-1">
                        <Pencil size={11} /> Edit
                      </button>
                    )}
                  </div>
                  {editingNotes ? (
                    <div>
                      <textarea
                        value={notesValue}
                        onChange={e => setNotesValue(e.target.value)}
                        className="w-full bg-zinc-900 border border-zinc-700 focus:border-blue-500/40 rounded-lg p-2.5 text-sm resize-none focus:outline-none transition-colors"
                        rows={3} placeholder="Add notes, ideas, context…" autoFocus
                      />
                      <div className="flex gap-2 mt-2">
                        <button onClick={handleSaveNotes} className="bg-blue-600 hover:bg-blue-500 text-white text-xs px-3 py-1.5 rounded-lg transition-colors">Save</button>
                        <button onClick={() => setEditingNotes(false)} className="text-zinc-600 text-xs hover:text-white transition-colors px-2">Cancel</button>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-zinc-300 leading-relaxed">
                      {selectedRiff.user_notes || <span className="text-zinc-600">No notes yet.</span>}
                    </p>
                  )}
                </div>

                {/* Find Similar */}
                <div>
                  <button
                    onClick={() => handleFindSimilar(selectedRiff.id)}
                    disabled={loadingSimilar || !selectedRiff.embedding_path}
                    className="flex items-center gap-2 text-sm text-zinc-500 hover:text-white hover:bg-zinc-800/60 px-3 py-2 rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                    title={!selectedRiff.embedding_path ? 'Re-analyze to generate embedding first' : ''}
                  >
                    <ListMusic size={14} />
                    {loadingSimilar ? 'Searching…' : 'Find Similar Riffs'}
                  </button>
                  {!selectedRiff.embedding_path && (
                    <p className="text-xs text-zinc-700 mt-1 pl-1">Re-analyze to enable similarity search.</p>
                  )}
                </div>

                {/* Similar results */}
                {similarResults && (
                  <div>
                    <p className="text-xs text-zinc-600 uppercase tracking-wider mb-3">Similar Riffs</p>
                    {similarResults.length === 0
                      ? <p className="text-sm text-zinc-600">No similar riffs with embeddings found.</p>
                      : similarResults.map(({ riff, similarity }) => (
                        <div key={riff.id}
                          onClick={() => { setSelectedRiff(riff); setSimilarResults(null); }}
                          className="flex items-center justify-between p-3 mb-1.5 rounded-lg bg-zinc-900/40 border border-zinc-800/40 hover:border-zinc-700 cursor-pointer transition-all">
                          <div className="flex items-center gap-3">
                            <FileAudio size={14} className="text-zinc-600 shrink-0" />
                            <div>
                              <p className="text-sm font-medium">{riff.title}</p>
                              <p className="text-xs text-zinc-600">{riff.bpm ? `${Math.round(riff.bpm)} BPM` : ''} {riff.key || ''}</p>
                            </div>
                          </div>
                          <span className="text-sm font-medium text-blue-400">{Math.round(similarity * 100)}% similar</span>
                        </div>
                      ))
                    }
                  </div>
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center min-h-64 text-center gap-3 border border-dashed border-zinc-800/50 rounded-xl p-16">
                <FileAudio size={32} className="text-zinc-700" />
                <p className="text-sm text-zinc-600">Select a riff to view details</p>
                <p className="text-xs text-zinc-700">Or drag & drop an audio file anywhere</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Single global sticky player ────────────────────────────────────── */}
      <StickyPlayer
        riff={playerRiff}
        audioUrl={playerUrl}
        isPlaying={globalIsPlaying}
        onClose={() => { setPlayerRiff(null); setPlayerUrl(null); setGlobalIsPlaying(false); }}
        onPlay={() => setGlobalIsPlaying(true)}
        onPause={() => setGlobalIsPlaying(false)}
        externalToggle={spacebarToggle}
      />
    </div>
  );
}
