import { useState, useRef } from 'react';
import { Mic, Square, Loader2 } from 'lucide-react';
import axios from 'axios';

const API_URL = 'http://localhost:8000/api/riffs';

export default function VoiceRecorder({ riffId, onUploadComplete }: { riffId: number, onUploadComplete: () => void }) {
  const [isRecording, setIsRecording] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<BlobPart[]>([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        await uploadVoiceNote(audioBlob);
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (error) {
      console.error('Error accessing microphone:', error);
      alert('Could not access microphone.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const uploadVoiceNote = async (blob: Blob) => {
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', blob, `voice_note_${riffId}.webm`);
      await axios.post(`${API_URL}/${riffId}/transcribe`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      onUploadComplete();
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="flex items-center gap-2">
      {isUploading ? (
        <span className="text-xs text-zinc-500 flex items-center gap-1"><Loader2 className="animate-spin" size={12}/> Transcribing...</span>
      ) : isRecording ? (
        <button onClick={stopRecording} className="text-xs bg-red-500/20 text-red-500 px-2 py-1 rounded flex items-center gap-1 hover:bg-red-500/30 transition-colors animate-pulse">
          <Square size={10} fill="currentColor" /> Stop Recording
        </button>
      ) : (
        <button onClick={startRecording} className="text-xs bg-zinc-800 text-zinc-300 px-2 py-1 rounded flex items-center gap-1 hover:bg-zinc-700 hover:text-white transition-colors">
          <Mic size={12} /> Record Voice Note
        </button>
      )}
    </div>
  );
}
