import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Upload, FileAudio, Search, RefreshCw, Trash2, RotateCcw, Mic, Sparkles, ListMusic, X } from 'lucide-react';
import WaveformPlayer from './components/WaveformPlayer';

const API = 'http://localhost:8000/api';
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
  tags: string | null;           // JSON string array
  ai_description: string | null;
  embedding_path: string | null;
};

type SearchResult = { riff: Riff; score: number | null; match_type: string };
type SimilarResult = { riff: Riff; similarity: number };

function parseTags(raw: string | null): string[] {
  if (!raw) return [];
  try { return JSON.parse(raw); } catch { return []; }
}

export default function App() {
  const [riffs, setRiffs]               = useState<Riff[]>([]);
  const [selectedRiff, setSelectedRiff] = useState<Riff | null>(null);
  const [searchQuery, setSearchQuery]   = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null);
  const [searching, setSearching]       = useState(false);
  const [similarResults, setSimilarResults] = useState<SimilarResult[] | null>(null);
  const [loadingSimilar, setLoadingSimilar] = useState(false);
  const [editingNotes, setEditingNotes] = useState(false);
  const [notesValue, setNotesValue]     = useState('');
  const voiceInputRef = useRef<HTMLInputElement>(null);

  // ── Polling ──────────────────────────────────────────────────────────────
  useEffect(() => {
    fetchRiffs();
    const id = setInterval(fetchRiffs, 3000);
    return () => clearInterval(id);
  }, []);

  const fetchRiffs = async () => {
    try {
      const { data } = await axios.get<Riff[]>(RIFFS_URL);
      setRiffs(data);
      setSelectedRiff(cur => cur ? data.find(r => r.id === cur.id) ?? cur : null);
    } catch {}
  };

  // ── Handlers ──────────────────────────────────────────────────────────────
  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const fd = new FormData(); fd.append('file', file);
    await axios.post(RIFFS_URL, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
    fetchRiffs();
    e.target.value = '';
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this riff?')) return;
    await axios.delete(`${RIFFS_URL}/${id}`);
    setSelectedRiff(null); setSimilarResults(null);
    fetchRiffs();
  };

  const handleReanalyze = async (id: number) => {
    await axios.post(`${RIFFS_URL}/${id}/analyze`);
    fetchRiffs();
  };

  const handleRetag = async (id: number) => {
    await axios.post(`${RIFFS_URL}/${id}/tag`);
    fetchRiffs();
  };

  const handleSearch = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!searchQuery.trim()) { setSearchResults(null); return; }
    setSearching(true);
    try {
      const { data } = await axios.get<SearchResult[]>(`${API}/search`, { params: { q: searchQuery } });
      setSearchResults(data);
    } finally { setSearching(false); }
  };

  const handleFindSimilar = async (id: number) => {
    setLoadingSimilar(true); setSimilarResults(null);
    try {
      const { data } = await axios.get<SimilarResult[]>(`${RIFFS_URL}/${id}/similar`);
      setSimilarResults(data);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Could not find similar riffs.');
    } finally { setLoadingSimilar(false); }
  };

  const handleVoiceNote = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !selectedRiff) return;
    const fd = new FormData(); fd.append('file', file);
    await axios.post(`${RIFFS_URL}/${selectedRiff.id}/transcribe`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    fetchRiffs();
    e.target.value = '';
  };

  const handleSaveNotes = async () => {
    if (!selectedRiff) return;
    await axios.patch(`${RIFFS_URL}/${selectedRiff.id}/notes`, { user_notes: notesValue });
    setEditingNotes(false);
    fetchRiffs();
  };

  const clearSearch = () => { setSearchQuery(''); setSearchResults(null); };

  // ── Derived ───────────────────────────────────────────────────────────────
  const listRiffs = searchResults ? searchResults.map(r => r.riff) : riffs;

  return (
    <div className="min-h-screen p-8 max-w-7xl mx-auto">
      {/* Header */}
      <header className="flex justify-between items-center mb-10">
        <div>
          <h1 className="text-4xl font-bold tracking-tight text-white">RiffVault</h1>
          <p className="text-zinc-500 text-sm mt-1">Your guitar ideas, searchable.</p>
        </div>
        <div className="flex gap-3">
          <button onClick={fetchRiffs} className="p-2 text-zinc-500 hover:text-white hover:bg-zinc-800 rounded transition-colors" title="Refresh">
            <RefreshCw size={18} />
          </button>
          <label className="cursor-pointer bg-zinc-800 hover:bg-zinc-700 px-4 py-2 rounded-lg flex items-center gap-2 text-sm transition-colors">
            <Upload size={16} />Import Riff
            <input type="file" className="hidden" accept=".wav,.mp3,.m4a" onChange={handleImport} />
          </label>
        </div>
      </header>

      {/* Search bar */}
      <form onSubmit={handleSearch} className="mb-8 relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500" size={18} />
        <input
          type="text"
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          placeholder='Search your riffs… "heavy Drop C riffs around 140 BPM"'
          className="w-full bg-zinc-900 border border-zinc-700 rounded-xl pl-11 pr-24 py-3 text-sm focus:outline-none focus:border-zinc-500 transition-colors"
        />
        <div className="absolute right-3 top-1/2 -translate-y-1/2 flex gap-2">
          {searchQuery && (
            <button type="button" onClick={clearSearch} className="text-zinc-500 hover:text-white transition-colors">
              <X size={16} />
            </button>
          )}
          <button type="submit" disabled={searching} className="bg-zinc-700 hover:bg-zinc-600 px-3 py-1 rounded-lg text-sm transition-colors disabled:opacity-50">
            {searching ? 'Searching…' : 'Search'}
          </button>
        </div>
      </form>

      {searchResults && (
        <p className="text-zinc-500 text-xs mb-4">{searchResults.length} result{searchResults.length !== 1 ? 's' : ''} for "{searchQuery}"</p>
      )}

      <div className="grid grid-cols-3 gap-8">
        {/* Sidebar */}
        <div className="col-span-1">
          <div className="flex flex-col gap-1.5">
            {listRiffs.map(riff => {
              const sr = searchResults?.find(r => r.riff.id === riff.id);
              return (
                <div
                  key={riff.id}
                  onClick={() => { setSelectedRiff(riff); setSimilarResults(null); }}
                  className={`p-3 rounded-lg cursor-pointer transition-colors ${selectedRiff?.id === riff.id ? 'bg-zinc-800 border border-zinc-700' : 'hover:bg-zinc-900 border border-transparent'}`}
                >
                  <div className="flex items-center gap-3">
                    <FileAudio size={20} className="text-zinc-500 shrink-0" />
                    <div className="min-w-0">
                      <h3 className="font-medium text-sm truncate" title={riff.title}>{riff.title}</h3>
                      <div className="flex gap-2 mt-0.5 flex-wrap">
                        {riff.bpm && <span className="text-xs text-zinc-500">{Math.round(riff.bpm)} BPM</span>}
                        {riff.key && <span className="text-xs text-zinc-500">{riff.key}</span>}
                        {sr?.score != null && <span className="text-xs text-blue-400">{Math.round(sr.score * 100)}% match</span>}
                        {riff.analysis_status === 'processing' && (
                          <span className="text-xs text-yellow-400">processing…</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
            {listRiffs.length === 0 && (
              <div className="text-center text-zinc-600 mt-12 text-sm">
                {searchResults ? 'No riffs matched your search.' : 'No riffs yet. Import one to get started.'}
              </div>
            )}
          </div>
        </div>

        {/* Detail panel */}
        <div className="col-span-2">
          {selectedRiff ? (
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-7 space-y-6">
              {/* Title + actions */}
              <div className="flex justify-between items-start">
                <div>
                  <h2 className="text-2xl font-bold leading-tight">{selectedRiff.title}</h2>
                  <p className="text-zinc-500 text-sm mt-1">{new Date(selectedRiff.created_at).toLocaleString()}</p>
                </div>
                <div className="flex gap-1">
                  <button onClick={() => handleRetag(selectedRiff.id)} className="p-2 text-zinc-500 hover:text-purple-400 hover:bg-zinc-800 rounded-lg transition-colors" title="Re-tag with LLM">
                    <Sparkles size={17} />
                  </button>
                  <button onClick={() => handleReanalyze(selectedRiff.id)} disabled={selectedRiff.analysis_status === 'processing'} className="p-2 text-zinc-500 hover:text-blue-400 hover:bg-zinc-800 rounded-lg transition-colors disabled:opacity-40" title="Re-analyze audio">
                    <RotateCcw size={17} />
                  </button>
                  <button onClick={() => handleDelete(selectedRiff.id)} className="p-2 text-zinc-500 hover:text-red-500 hover:bg-zinc-800 rounded-lg transition-colors" title="Delete">
                    <Trash2 size={17} />
                  </button>
                </div>
              </div>

              {/* Waveform */}
              <WaveformPlayer url={`${RIFFS_URL}/${selectedRiff.id}/audio`} />

              {/* Analysis progress */}
              {selectedRiff.analysis_status === 'processing' && (
                <div>
                  <div className="flex justify-between text-xs text-zinc-500 mb-1">
                    <span>Analyzing…</span>
                    <span>{Math.round((selectedRiff.analysis_progress || 0) * 100)}%</span>
                  </div>
                  <div className="w-full bg-zinc-800 rounded-full h-1.5">
                    <div className="bg-yellow-400 h-1.5 rounded-full transition-all duration-500" style={{ width: `${(selectedRiff.analysis_progress || 0) * 100}%` }} />
                  </div>
                </div>
              )}

              {/* Metadata grid */}
              <div className="grid grid-cols-4 gap-3">
                {[
                  { label: 'Status', value: selectedRiff.analysis_status, color: selectedRiff.analysis_status === 'completed' ? 'text-green-400' : selectedRiff.analysis_status === 'failed' ? 'text-red-400' : 'text-yellow-400' },
                  { label: 'BPM', value: selectedRiff.bpm ? Math.round(selectedRiff.bpm) : '--' },
                  { label: 'Key', value: selectedRiff.key || '--' },
                  { label: 'Duration', value: selectedRiff.duration ? `${selectedRiff.duration.toFixed(1)}s` : '--' },
                ].map(({ label, value, color }) => (
                  <div key={label} className="bg-zinc-950 p-3 rounded-lg border border-zinc-800">
                    <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-1">{label}</p>
                    <p className={`text-sm font-medium capitalize ${color || ''}`}>{String(value)}</p>
                  </div>
                ))}
              </div>

              {/* AI description */}
              {selectedRiff.ai_description && (
                <div className="bg-zinc-950 border border-zinc-800 rounded-lg p-4">
                  <p className="text-xs font-semibold text-purple-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <Sparkles size={12} /> AI Description <span className="text-zinc-600 font-normal normal-case">(estimated)</span>
                  </p>
                  <p className="text-sm text-zinc-300">{selectedRiff.ai_description}</p>
                </div>
              )}

              {/* Tags */}
              {parseTags(selectedRiff.tags).length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">Tags</p>
                  <div className="flex flex-wrap gap-2">
                    {parseTags(selectedRiff.tags).map(tag => (
                      <span key={tag} className="bg-zinc-800 text-zinc-300 text-xs px-2.5 py-1 rounded-full">{tag}</span>
                    ))}
                  </div>
                </div>
              )}

              {/* Voice note transcript */}
              <div className="bg-zinc-950 border border-zinc-800 rounded-lg p-4">
                <div className="flex justify-between items-center mb-2">
                  <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider flex items-center gap-1.5">
                    <Mic size={12} /> Voice Note
                  </p>
                  <label className="cursor-pointer text-xs text-zinc-500 hover:text-white transition-colors flex items-center gap-1">
                    <Upload size={12} /> Upload voice note
                    <input ref={voiceInputRef} type="file" className="hidden" accept=".wav,.mp3,.m4a,.ogg" onChange={handleVoiceNote} />
                  </label>
                </div>
                {selectedRiff.voice_note_transcript
                  ? <p className="text-sm text-zinc-300 italic">"{selectedRiff.voice_note_transcript}"</p>
                  : <p className="text-sm text-zinc-600">No voice note yet. Upload an audio note to transcribe it locally.</p>
                }
              </div>

              {/* User notes */}
              <div className="bg-zinc-950 border border-zinc-800 rounded-lg p-4">
                <div className="flex justify-between items-center mb-2">
                  <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Notes</p>
                  {!editingNotes && (
                    <button onClick={() => { setEditingNotes(true); setNotesValue(selectedRiff.user_notes || ''); }}
                      className="text-xs text-zinc-500 hover:text-white transition-colors">Edit</button>
                  )}
                </div>
                {editingNotes ? (
                  <div>
                    <textarea
                      value={notesValue}
                      onChange={e => setNotesValue(e.target.value)}
                      className="w-full bg-zinc-900 border border-zinc-700 rounded p-2 text-sm resize-none focus:outline-none focus:border-zinc-500"
                      rows={3}
                      placeholder="Add notes, ideas, context…"
                    />
                    <div className="flex gap-2 mt-2">
                      <button onClick={handleSaveNotes} className="bg-white text-black text-xs px-3 py-1 rounded-lg hover:bg-zinc-200 transition-colors">Save</button>
                      <button onClick={() => setEditingNotes(false)} className="text-zinc-500 text-xs hover:text-white transition-colors">Cancel</button>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-zinc-300">{selectedRiff.user_notes || <span className="text-zinc-600">No notes yet.</span>}</p>
                )}
              </div>

              {/* Find Similar */}
              <div>
                <button
                  onClick={() => handleFindSimilar(selectedRiff.id)}
                  disabled={loadingSimilar || !selectedRiff.embedding_path}
                  className="flex items-center gap-2 bg-zinc-800 hover:bg-zinc-700 px-4 py-2 rounded-lg text-sm transition-colors disabled:opacity-40"
                  title={!selectedRiff.embedding_path ? 'Re-analyze to generate embedding first' : ''}
                >
                  <ListMusic size={16} />
                  {loadingSimilar ? 'Searching…' : 'Find Similar Riffs'}
                </button>
                {!selectedRiff.embedding_path && (
                  <p className="text-xs text-zinc-600 mt-1">Re-analyze to enable similarity search.</p>
                )}
              </div>

              {/* Similar results */}
              {similarResults && (
                <div>
                  <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3">Similar Riffs</p>
                  {similarResults.length === 0
                    ? <p className="text-sm text-zinc-600">No other riffs with embeddings found.</p>
                    : similarResults.map(({ riff, similarity }) => (
                      <div key={riff.id} onClick={() => { setSelectedRiff(riff); setSimilarResults(null); }}
                        className="flex items-center justify-between p-3 mb-1.5 rounded-lg bg-zinc-950 border border-zinc-800 hover:border-zinc-600 cursor-pointer transition-colors">
                        <div className="flex items-center gap-3">
                          <FileAudio size={16} className="text-zinc-500 shrink-0" />
                          <div>
                            <p className="text-sm font-medium truncate max-w-xs">{riff.title}</p>
                            <p className="text-xs text-zinc-500">{riff.bpm ? `${Math.round(riff.bpm)} BPM` : ''} {riff.key || ''}</p>
                          </div>
                        </div>
                        <span className="text-sm font-semibold text-blue-400 shrink-0">{Math.round(similarity * 100)}% similar</span>
                      </div>
                    ))
                  }
                </div>
              )}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-zinc-600 border border-dashed border-zinc-800 rounded-xl p-16">
              <FileAudio size={48} className="mb-4 opacity-40" />
              <p className="text-sm">Select a riff or search to get started.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
