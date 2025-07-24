import asyncio
from mentor.core.engine.utils import text_to_speech

async def test_tts():
    text = "Hello, this is a test of the text-to-speech function."
    print(f"Testing TTS for: '{text}'")
    try:
        audio_bytes = await text_to_speech(text)
        if audio_bytes:
            print(f"Successfully generated {len(audio_bytes)} bytes of audio.")
            # Optionally save to file to verify
            with open("test_audio.mp3", "wb") as f:
                f.write(audio_bytes)
            print("Audio saved to test_audio.mp3")
        else:
            print("TTS function returned no audio data.")
    except Exception as e:
        print(f"Error during TTS test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_tts())