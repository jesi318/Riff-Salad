import traceback
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_ollama():
    print("--- Testing Ollama ---")
    try:
        import ollama
        from app.core.config import LLM_MODEL
        print(f"Using model: {LLM_MODEL}")
        models = ollama.list()
        print(f"Available models: {[m['name'] for m in models.get('models', [])]}")
        response = ollama.chat(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": "Say hello!"}],
        )
        print("Ollama response:", response["message"]["content"])
    except Exception as e:
        print("Ollama failed!")
        traceback.print_exc()

def test_whisper():
    print("\n--- Testing Whisper ---")
    try:
        from app.ai.transcription import get_transcription_service
        service = get_transcription_service()
        # Find any audio file
        audio_file = "../data/audio/Sl-do.mp3"
        print(f"Transcribing {audio_file}...")
        text = service.transcribe(audio_file)
        print("Whisper response:", text)
    except Exception as e:
        print("Whisper failed!")
        traceback.print_exc()

test_ollama()
test_whisper()
