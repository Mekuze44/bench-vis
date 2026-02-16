# teste_voz_headless.py
from gtts import gTTS
import tempfile
import subprocess
import os
import shutil

def testar_voz(texto="Olá! Teste de voz headless"):
    print(f"Testando: {texto}")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
        temp_file = tmp.name
    
    try:
        # Gerar áudio
        tts = gTTS(text=texto, lang='pt', slow=False)
        tts.save(temp_file)
        print("✅ Áudio gerado")
        
        # Testar players
        players_teste = [
            ('ffplay', ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', temp_file]),
            ('mpg123', ['mpg123', '-q', temp_file]),
            ('mpv', ['mpv', '--no-video', '--quiet', temp_file]),
        ]
        
        for nome, cmd in players_teste:
            if shutil.which(nome):
                print(f"🎵 Testando {nome}...")
                try:
                    subprocess.run(cmd, check=True, timeout=10)
                    print(f"✅ {nome} funcionou!")
                    break
                except:
                    print(f"❌ {nome} falhou")
            else:
                print(f"⚠️ {nome} não instalado")
        
    finally:
        os.unlink(temp_file)

if __name__ == "__main__":
    testar_voz()