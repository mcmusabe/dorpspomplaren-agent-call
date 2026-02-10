#!/usr/bin/env python3
"""
List alle beschikbare voices in Retell
"""

import os
from retell import Retell
from config import RETELL_API_KEY

def main():
    print("=" * 60)
    print("Retell Available Voices")
    print("=" * 60)
    print()
    
    client = Retell(api_key=RETELL_API_KEY)
    
    try:
        voices_response = client.voice.list()
        
        # Handle both dict and object responses
        if hasattr(voices_response, 'voices'):
            voices = voices_response.voices
        elif isinstance(voices_response, dict):
            voices = voices_response.get('voices', [])
        else:
            voices = list(voices_response) if hasattr(voices_response, '__iter__') else []
        
        if not voices or len(voices) == 0:
            print("❌ Geen voices gevonden")
            return 1
        
        print(f"✅ {len(voices)} voice(s) beschikbaar:\n")
        
        for i, voice in enumerate(voices, 1):
            if hasattr(voice, 'voice_id'):
                voice_id = voice.voice_id
                voice_name = getattr(voice, 'name', 'N/A')
                voice_language = getattr(voice, 'language', 'N/A')
            elif isinstance(voice, dict):
                voice_id = voice.get('voice_id', 'N/A')
                voice_name = voice.get('name', 'N/A')
                voice_language = voice.get('language', 'N/A')
            else:
                voice_id = str(voice)
                voice_name = 'N/A'
                voice_language = 'N/A'
            
            print(f"{i}. voice_id: {voice_id}")
            print(f"   name: {voice_name}")
            print(f"   language: {voice_language}")
            print()
        
        print("=" * 60)
        print("💡 TIP: Zet RETELL_VOICE_ID env var om een specifieke voice te gebruiken")
        print("   export RETELL_VOICE_ID='<voice_id>'")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"❌ Fout bij ophalen voices: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())

