import { useState, useEffect } from 'react';
import axios from 'axios';
import { Play, Pause, Upload, FileAudio, Search } from 'lucide-react';
import WaveformPlayer from './components/WaveformPlayer';

const API_URL = 'http://localhost:8000/api/riffs';

function App() {
  const [riffs, setRiffs] = useState<any[]>([]);
  const [selectedRiff, setSelectedRiff] = useState<any | null>(null);

  useEffect(() => {
    fetchRiffs();
  }, []);

  const fetchRiffs = async () => {
    try {
      const response = await axios.get(API_URL);
      setRiffs(response.data);
    } catch (error) {
      console.error('Error fetching riffs', error);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      await axios.post(API_URL, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      fetchRiffs();
    } catch (error) {
      console.error('Error uploading file', error);
    }
  };

  return (
    <div className="min-h-screen p-8 max-w-6xl mx-auto">
      <header className="flex justify-between items-center mb-12">
        <h1 className="text-4xl font-bold tracking-tight text-white">RiffVault</h1>
        <div>
          <label className="cursor-pointer bg-zinc-800 hover:bg-zinc-700 px-4 py-2 rounded flex items-center gap-2">
            <Upload size={20} />
            <span>Import Riff</span>
            <input type="file" className="hidden" accept=".wav,.mp3,.m4a" onChange={handleFileUpload} />
          </label>
        </div>
      </header>

      <div className="grid grid-cols-3 gap-8">
        <div className="col-span-1 border-r border-zinc-800 pr-8">
          <div className="relative mb-6">
            <Search className="absolute left-3 top-3 text-zinc-500" size={18} />
            <input 
              type="text" 
              placeholder="Search your riffs..." 
              className="w-full bg-zinc-900 border border-zinc-800 rounded pl-10 pr-4 py-2 text-sm focus:outline-none focus:border-zinc-600"
            />
          </div>
          <div className="flex flex-col gap-2">
            {riffs.map(riff => (
              <div 
                key={riff.id} 
                onClick={() => setSelectedRiff(riff)}
                className={`p-4 rounded cursor-pointer transition-colors ${selectedRiff?.id === riff.id ? 'bg-zinc-800' : 'hover:bg-zinc-900'}`}
              >
                <div className="flex items-center gap-3">
                  <FileAudio size={24} className="text-zinc-400" />
                  <div>
                    <h3 className="font-medium truncate" title={riff.title}>{riff.title}</h3>
                    <p className="text-xs text-zinc-500">{new Date(riff.created_at).toLocaleDateString()}</p>
                  </div>
                </div>
              </div>
            ))}
            {riffs.length === 0 && (
              <div className="text-center text-zinc-500 mt-8 text-sm">
                No riffs found. Import one to get started.
              </div>
            )}
          </div>
        </div>

        <div className="col-span-2">
          {selectedRiff ? (
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-8">
              <h2 className="text-3xl font-bold mb-2">{selectedRiff.title}</h2>
              <p className="text-zinc-500 mb-8">Recorded on {new Date(selectedRiff.created_at).toLocaleString()}</p>
              
              <div className="mb-8">
                <WaveformPlayer url={`${API_URL}/${selectedRiff.id}/audio`} />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-zinc-950 p-4 rounded border border-zinc-800">
                  <h4 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-1">Status</h4>
                  <p className="text-sm">Audio imported</p>
                </div>
                <div className="bg-zinc-950 p-4 rounded border border-zinc-800">
                  <h4 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-1">Intelligence</h4>
                  <p className="text-sm text-zinc-600 italic">Analysis available in Milestone 2</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-zinc-500 border border-dashed border-zinc-800 rounded-lg p-12">
              <FileAudio size={48} className="mb-4 opacity-50" />
              <p>Select a riff to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
