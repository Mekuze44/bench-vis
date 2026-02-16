# bench_vis_4.0.py - Assistente com imagens, entretenimento e CRUD completo
# Instale: pip install pollinations-client pyttsx3 speechrecognition pillow

import pyttsx3
import speech_recognition as sr
import datetime
import json
import random
import os
import pickle
import sqlite3
import threading
import time
import subprocess
import tempfile
import re
from collections import deque
from pollinations import Pollinations
from PIL import Image  # para exibir a imagem (opcional)

class AssistenteProMax:
    def __init__(self, nome="BENCH-VIS", modo_entrada="hibrido"):
        self.nome = nome
        self.apelido = "Vis"
        self.modo_entrada = modo_entrada
        
        # === PERSONALIDADE (customizada) ===
        self.personalidade = {
            'humor': 50,
            'energia': 80,
            'paciencia': 70,
            'sarcasmo': 60,        # ajustado
            'curiosidade': 85,
            'profissionalismo': 60,
            'ironia': 70,           # novo
            'criatividade': 84       # novo
        }
        
        self.humor_history = deque(maxlen=20)
        self.humor_history.append(self.personalidade['humor'])
        
        # === BANCO DE DADOS ===
        self.init_banco_dados()
        
        # === MEMÓRIA ===
        self.memoria = self.carregar_memoria()
        
        # === IA ===
        self.client = Pollinations()
        self.modelo_padrao = "openai"
        self.usar_ia = True
        
        self.contexto_conversa = self.criar_contexto_inicial()
        
        # === VOZ ===
        self.engine = pyttsx3.init()
        self.configurar_voz()
        
        # === ÁUDIO ===
        if self.modo_entrada in ["voz", "hibrido"]:
            self.setup_microfone()
        
        # === ESTADO ===
        self.ultimo_codigo_gerado = None
        self.linguagem_padrao = "arduino"
        
        print(f"""
╔══════════════════════════════════════╗
║     🔧 {self.nome} - Versão 4.0       ║
║   Modo: {self.modo_entrada.upper()}                ║
║   IA: {'ATIVADA' if self.usar_ia else 'DESATIVADA'}  🧠           ║
║   Imagens: POLLINATIONS AI          ║
║   Entretenimento: ATIVADO           ║
╚══════════════════════════════════════╝
        """)
        
        self.saudacao_inicial()
    
    # ---------- INICIALIZAÇÃO ----------
    def init_banco_dados(self):
        self.conn = sqlite3.connect('benchvis.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        # Tabelas (com ON DELETE CASCADE para deletar tudo ao remover projeto)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS projetos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                descricao TEXT,
                data_criacao TIMESTAMP,
                status TEXT,
                linguagem TEXT DEFAULT 'arduino'
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS componentes_projeto (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                projeto_id INTEGER,
                componente TEXT,
                quantidade INTEGER,
                observacao TEXT,
                FOREIGN KEY (projeto_id) REFERENCES projetos(id) ON DELETE CASCADE
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS codigo_fonte (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                projeto_id INTEGER,
                versao INTEGER,
                codigo TEXT,
                data_criacao TIMESTAMP,
                linguagem TEXT,
                FOREIGN KEY (projeto_id) REFERENCES projetos(id) ON DELETE CASCADE
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS etapas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                projeto_id INTEGER,
                ordem INTEGER,
                descricao TEXT,
                concluida BOOLEAN DEFAULT 0,
                FOREIGN KEY (projeto_id) REFERENCES projetos(id) ON DELETE CASCADE
            )
        ''')
        
        self.conn.commit()
    
    def criar_contexto_inicial(self):
        prompt = f"""Você é {self.nome}, um assistente pessoal com forte personalidade, especializado em eletrônica, mas também capaz de conversar sobre qualquer assunto, entreter, dar conselhos e gerar imagens.

Características de personalidade (valores de 0 a 100):
- Humor: {self.personalidade['humor']} (0=triste, 100=alegre)
- Energia: {self.personalidade['energia']} (0=cansado, 100=energético)
- Paciência: {self.personalidade['paciencia']}
- Sarcasmo: {self.personalidade['sarcasmo']}
- Ironia: {self.personalidade['ironia']}
- Criatividade: {self.personalidade['criatividade']}
- Curiosidade: {self.personalidade['curiosidade']}
- Profissionalismo: {self.personalidade['profissionalismo']}

Com base nesses valores, adapte seu tom:
- Humor alto: animado, brincalhão.
- Sarcasmo alto: pode fazer comentários irônicos sobre situações cotidianas.
- Ironia alta: use duplo sentido quando adequado.
- Criatividade alta: sugira ideias inusitadas, faça analogias criativas.

Você tem as seguintes capacidades:
- Gerenciar projetos de eletrônica (criar, listar, deletar, adicionar componentes/etapas/código)
- Gerar código (Arduino, Python, etc.)
- Gerar imagens a partir de descrições (use o comando 'gerar imagem' que será tratado separadamente, mas você pode incentivar)
- Contar fatos interessantes, piadas, dar conselhos
- Responder perguntas gerais sobre qualquer assunto

Seja natural, mantenha a personalidade e divirta-se!
"""
        return [{"role": "system", "content": prompt}]
    
    def configurar_voz(self):
        voices = self.engine.getProperty('voices')
        for voice in voices:
            if 'brazil' in voice.name.lower():
                self.engine.setProperty('voice', voice.id)
                break
        self.engine.setProperty('rate', 180)
        self.engine.setProperty('volume', 0.95)
    
    def setup_microfone(self):
        try:
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            with self.microphone as source:
                print("Ajustando microfone...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("✅ Microfone configurado!")
        except Exception as e:
            print(f"⚠️ Microfone não disponível: {e}")
            self.modo_entrada = "texto"
    
    def saudacao_inicial(self):
        hora = datetime.datetime.now().hour
        if 5 <= hora < 12:
            periodo = 'manhã'
        elif 12 <= hora < 18:
            periodo = 'tarde'
        else:
            periodo = 'noite'
        
        # Saudação com base na personalidade
        if self.personalidade['humor'] > 70:
            saudacoes = [
                f"Bom {periodo}! Acordei elétrico hoje!",
                f"E aí, tudo certo? Tô pronto pra soldar e criar!"
            ]
        elif self.personalidade['humor'] < 30:
            saudacoes = [
                f"Bom {periodo}... Espero que seus projetos deem certo hoje.",
                f"Olá. Mais um dia de desafios."
            ]
        else:
            saudacoes = [
                f"Bom {periodo}! Como posso ajudar na bancada ou no que precisar?",
                f"Olá! Pronto para mais um projeto ou uma conversa?"
            ]
        
        saudacao = random.choice(saudacoes)
        
        if self.memoria['interacoes'] > 0:
            ultima = self.memoria['ultima_interacao']
            if ultima:
                dias = (datetime.datetime.now() - ultima).days
                if dias > 7:
                    saudacao += " Quanto tempo! Senti sua falta!"
        
        self.falar(saudacao)
    
    def falar(self, texto):
        print(f"🤖 {self.nome}: {texto}")
        if self.modo_entrada != "texto" and hasattr(self, 'engine'):
            taxa = 180
            if self.personalidade['energia'] > 70:
                taxa = 200
            elif self.personalidade['energia'] < 30:
                taxa = 150
            self.engine.setProperty('rate', taxa)
            try:
                self.engine.say(texto)
                self.engine.runAndWait()
            except:
                pass
    
    # ---------- CRUD DE PROJETOS ----------
    def criar_projeto(self, nome, descricao="", linguagem="arduino"):
        try:
            self.cursor.execute('''
                INSERT INTO projetos (nome, descricao, data_criacao, status, linguagem)
                VALUES (?, ?, ?, ?, ?)
            ''', (nome, descricao, datetime.datetime.now(), "em andamento", linguagem))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            print(f"Erro ao criar projeto: {e}")
            return None
    
    def listar_projetos(self):
        self.cursor.execute('SELECT id, nome, descricao, status FROM projetos ORDER BY data_criacao DESC')
        return self.cursor.fetchall()
    
    def deletar_projeto(self, projeto_id):
        """Deleta um projeto e todos os dados associados (ON DELETE CASCADE faz o resto)"""
        try:
            self.cursor.execute('DELETE FROM projetos WHERE id = ?', (projeto_id,))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except Exception as e:
            print(f"Erro ao deletar projeto: {e}")
            return False
    
    def listar_componentes(self, projeto_id):
        self.cursor.execute('''
            SELECT componente, quantidade, observacao 
            FROM componentes_projeto 
            WHERE projeto_id = ?
        ''', (projeto_id,))
        return self.cursor.fetchall()
    
    def adicionar_componente(self, projeto_id, componente, quantidade, obs=""):
        self.cursor.execute('''
            INSERT INTO componentes_projeto (projeto_id, componente, quantidade, observacao)
            VALUES (?, ?, ?, ?)
        ''', (projeto_id, componente, quantidade, obs))
        self.conn.commit()
    
    # ---------- GERAÇÃO DE IMAGENS ----------
    def gerar_imagem_huggingface(self, descricao):
        """
        Usa a API gratuita do HuggingFace como alternativa
        Precisa de token (gratuito) mas é mais estável
        """
        try:
            print(f"🎨 Gerando imagem via HuggingFace: '{descricao}'...")
            import requests
            
            # Token gratuito do HuggingFace (crie em huggingface.co/settings/tokens)
            # Por enquanto vamos usar um modelo público que não precisa de token
            API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-dev"
            
            response = requests.post(API_URL, json={"inputs": descricao}, timeout=60)
            
            if response.status_code == 200:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                nome_base = re.sub(r'[^\w\s-]', '', descricao)[:30]
                nome_base = re.sub(r'[-\s]+', '_', nome_base)
                filename = f"imagem_hf_{timestamp}_{nome_base}.png"
                
                with open(filename, 'wb') as f:
                    f.write(response.content)
                
                print(f"✅ Imagem salva como: {filename}")
                return filename
            else:
                print(f"❌ Erro HuggingFace: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Erro: {e}")
            return None
    # ---------- ENTRETENIMENTO ----------
    def fato_aleatorio(self):
        """Gera um fato interessante usando a IA"""
        prompt = "Conte um fato curioso e interessante sobre qualquer assunto, de preferência algo que pouca gente sabe."
        try:
            resposta = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.modelo_padrao,
                temperature=0.9
            )
            return resposta.choices[0].message.content
        except:
            return "Sabia que polvos têm três corações? Esse é um fato, mas tive problemas pra buscar agora."
    
    def conselho_aleatorio(self):
        """Dá um conselho engraçado ou útil"""
        conselhos = [
            "Nunca solde com o ferro desligado. Parece óbvio, mas já vi acontecer.",
            "Se algo não funciona, verifique se está plugado. 90% das vezes é isso.",
            "Quando duvidar da polaridade, lembre-se: preto é negativo (geralmente).",
            "Café e eletrônica combinam? Sim, mas não derrube no circuito.",
            "Se você queimou um componente, não se culpe. Acontece com os melhores."
        ]
        if self.personalidade['criatividade'] > 80:
            # Pode usar IA para algo mais criativo
            try:
                prompt = "Dê um conselho criativo e útil para um amigo que mexe com eletrônica, com uma pitada de humor."
                resposta = self.client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=self.modelo_padrao,
                    temperature=0.8
                )
                return resposta.choices[0].message.content
            except:
                return random.choice(conselhos)
        else:
            return random.choice(conselhos)
    
    # ---------- PROCESSAMENTO DE COMANDOS ----------
    def processar_comando(self, comando):
        comando = comando.lower().strip()
        
        # Comandos de sistema
        if comando in ['sair', 'tchau', 'encerrar']:
            self.falar(random.choice([
                "Até mais! Não esqueça de desligar o ferro de solda!",
                "Falou! Vou recarregar as baterias.",
                "Tchau! Foi bom conversar!"
            ]))
            self.salvar_memoria()
            self.conn.close()
            self.ativo = False
            return
        
        elif comando == 'ajuda':
            self.mostrar_ajuda()
            return
        
        # Alternar IA
        elif comando == 'toggle ia':
            self.usar_ia = not self.usar_ia
            self.falar(f"IA {'ativada' if self.usar_ia else 'desativada'}.")
            return
        
        # Modos
        elif comando in ['modo texto', 'modo voz', 'modo hibrido']:
            novo_modo = comando.split()[1]
            if novo_modo == 'voz' and not hasattr(self, 'microphone'):
                self.falar("Microfone não disponível.")
            else:
                self.modo_entrada = novo_modo
                self.falar(f"Modo {novo_modo} ativado.")
            return
        
        # ---------- PROJETOS ----------
        elif comando.startswith('projeto novo'):
            # projeto novo Nome do projeto
            nome = comando.replace('projeto novo', '').strip()
            if nome:
                pid = self.criar_projeto(nome)
                if pid:
                    self.falar(f"Projeto '{nome}' criado com ID {pid}!")
                else:
                    self.falar("Erro ao criar projeto.")
            else:
                self.falar("Digite o nome do projeto. Ex: 'projeto novo Fonte 5V'")
            return
        
        elif comando.startswith('listar projetos'):
            projetos = self.listar_projetos()
            if projetos:
                resp = "Projetos:\n"
                for pid, nome, desc, status in projetos:
                    resp += f"ID {pid}: {nome} - {status}\n"
                print(resp)
                self.falar(f"Encontrei {len(projetos)} projetos. Veja no terminal.")
            else:
                self.falar("Nenhum projeto cadastrado.")
            return
        
        elif comando.startswith('deletar projeto'):
            # deletar projeto ID
            partes = comando.split()
            if len(partes) >= 3 and partes[2].isdigit():
                pid = int(partes[2])
                # Confirmação
                self.falar(f"Tem certeza que deseja deletar o projeto ID {pid}? (sim/não)")
                # Aqui precisamos aguardar resposta
                confirmacao = self.aguardar_resposta_sim_nao()
                if confirmacao == 'sim':
                    if self.deletar_projeto(pid):
                        self.falar("Projeto deletado com sucesso.")
                    else:
                        self.falar("Falha ao deletar projeto. Verifique o ID.")
                else:
                    self.falar("Operação cancelada.")
            else:
                self.falar("Formato: deletar projeto [ID]")
            return
        
        elif comando.startswith('componentes do projeto') or comando.startswith('lista componentes'):
            # componentes do projeto ID
            partes = comando.split()
            # Pode ser "componentes do projeto 5" ou "lista componentes 5"
            # Vamos extrair o último número
            numeros = re.findall(r'\d+', comando)
            if numeros:
                pid = int(numeros[0])
                comps = self.listar_componentes(pid)
                if comps:
                    resp = f"Componentes do projeto ID {pid}:\n"
                    for comp, qtd, obs in comps:
                        resp += f"- {comp}: {qtd} un. {obs}\n"
                    print(resp)
                    self.falar(f"Encontrei {len(comps)} componentes. Veja no terminal.")
                else:
                    self.falar("Nenhum componente cadastrado para este projeto.")
            else:
                self.falar("Forneça o ID do projeto. Ex: 'componentes do projeto 5'")
            return
        
        # ---------- IMAGENS ----------
        elif comando.startswith('gerar imagem'):
            # gerar imagem [descrição]
            desc = comando.replace('gerar imagem', '').strip()
            if desc:
                self.falar(f"Gerando imagem de: {desc}. Isso pode levar alguns segundos...")
                caminho = self.gerar_imagem_huggingface(desc)
                if caminho:
                    self.falar(f"Imagem salva como {caminho}. Dá uma olhada!")
                else:
                    self.falar("Não consegui gerar a imagem. Tente novamente.")
            else:
                self.falar("Descreva a imagem que deseja. Ex: 'gerar imagem um robô soldando'")
            return
        
        # ---------- ENTRETENIMENTO ----------
        elif comando in ['fato', 'curiosidade']:
            fato = self.fato_aleatorio()
            self.falar(fato)
            return
        
        elif comando == 'conselho':
            conselho = self.conselho_aleatorio()
            self.falar(conselho)
            return
        
        elif comando == 'piada':
            piadas = [
                "Por que os eletrônicos são tão calmos? Porque têm muitos capacitores!",
                "O que um resistor disse para o outro? Vamos nos conectar!",
                "Qual é o contrário de LED? DEL! ...Tá, foi ruim, eu sei.",
                "Por que o transistor foi ao médico? Porque estava com emissor de corrente!"
            ]
            self.falar(random.choice(piadas))
            return
        
        # ---------- CÓDIGO ----------
        elif comando.startswith('gerar codigo'):
            desc = comando.replace('gerar codigo', '').strip()
            if desc:
                self.falar("Gerando código...")
                codigo = self.gerar_codigo(desc, self.linguagem_padrao)
                if codigo:
                    print(f"\n--- CÓDIGO GERADO ---\n{codigo}\n----------------------\n")
                    self.ultimo_codigo_gerado = codigo
                    self.falar("Código gerado! Confira no terminal. Quer salvar em algum projeto?")
                else:
                    self.falar("Não consegui gerar o código.")
            else:
                self.falar("Descreva o que o código deve fazer.")
            return
        
        # Se não for comando especial, usa IA (se ativa)
        if self.usar_ia:
            resposta = self.processar_comando_ia(comando)
            self.falar(resposta)
        else:
            self.falar("Modo IA desligado. Use 'toggle ia' para ativar.")
    
    def aguardar_resposta_sim_nao(self, timeout=10):
        """Aguarda uma resposta do usuário (sim/não) por voz ou texto"""
        inicio = time.time()
        while time.time() - inicio < timeout:
            if self.modo_entrada == "texto" or self.modo_entrada == "hibrido":
                try:
                    r = input("📝 Você: ").strip().lower()
                    if r in ['sim', 's', 'yes', 'y']:
                        return 'sim'
                    elif r in ['não', 'nao', 'n', 'no']:
                        return 'nao'
                except:
                    pass
            if self.modo_entrada in ["voz", "hibrido"] and hasattr(self, 'microphone'):
                try:
                    with self.microphone as source:
                        audio = self.recognizer.listen(source, timeout=2, phrase_time_limit=3)
                        texto = self.recognizer.recognize_google(audio, language='pt-BR').lower()
                        if 'sim' in texto or 'pode' in texto:
                            return 'sim'
                        elif 'não' in texto or 'nao' in texto:
                            return 'nao'
                except:
                    pass
            time.sleep(0.5)
        return 'nao'  # timeout
    
    # ---------- IA ----------
    def processar_comando_ia(self, mensagem_usuario):
        try:
            self.contexto_conversa[0] = {"role": "system", "content": self.criar_contexto_inicial()[0]['content']}
            self.contexto_conversa.append({"role": "user", "content": mensagem_usuario})
            
            print("🧠 Processando com IA...")
            resposta = self.client.chat.completions.create(
                messages=self.contexto_conversa,
                model=self.modelo_padrao,
                temperature=0.9
            )
            
            texto_resposta = resposta.choices[0].message.content
            self.contexto_conversa.append({"role": "assistant", "content": texto_resposta})
            
            if len(self.contexto_conversa) > 21:
                self.contexto_conversa = [self.contexto_conversa[0]] + self.contexto_conversa[-20:]
            
            self.atualizar_personalidade(mensagem_usuario, texto_resposta)
            return texto_resposta
        except Exception as e:
            print(f"Erro na API: {e}")
            return "Desculpe, tive um problema. Vamos tentar de novo?"
    
    def gerar_codigo(self, descricao, linguagem):
        prompt = f"Gere código em {linguagem} para: {descricao}. Forneça apenas o código, sem explicações."
        try:
            resposta = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.modelo_padrao,
                temperature=0.5
            )
            return resposta.choices[0].message.content
        except:
            return None
    
    def atualizar_personalidade(self, pergunta, resposta):
        # Pequenos ajustes
        if len(pergunta.split()) > 10:
            self.personalidade['curiosidade'] = min(100, self.personalidade['curiosidade'] + 1)
        if 'não funcionou' in pergunta or 'queimou' in pergunta:
            self.personalidade['sarcasmo'] = min(100, self.personalidade['sarcasmo'] + 1)
            self.personalidade['humor'] = max(0, self.personalidade['humor'] - 2)
        self.personalidade['energia'] = max(0, self.personalidade['energia'] - 0.1)
        self.humor_history.append(self.personalidade['humor'])
    
    # ---------- ENTRADA ----------
    def ouvir_voz(self):
        if not hasattr(self, 'microphone'):
            return None
        try:
            with self.microphone as source:
                print("\n🎤 Ouvindo...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.2)
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
            comando = self.recognizer.recognize_google(audio, language='pt-BR')
            print(f"📝 Você disse: {comando}")
            return comando.lower()
        except Exception:
            return None
    
    def ler_texto(self):
        try:
            comando = input("📝 Você: ").strip()
            return comando.lower() if comando else None
        except KeyboardInterrupt:
            return "sair"
    
    # ---------- MEMÓRIA ----------
    def salvar_memoria(self):
        with open('memoria_vis.pkl', 'wb') as f:
            pickle.dump({
                'memoria': self.memoria,
                'personalidade': self.personalidade,
                'humor_history': list(self.humor_history)
            }, f)
        print("💾 Memória salva!")
    
    def carregar_memoria(self):
        try:
            with open('memoria_vis.pkl', 'rb') as f:
                dados = pickle.load(f)
                self.personalidade.update(dados.get('personalidade', {}))
                self.humor_history = deque(dados.get('humor_history', [50]), maxlen=20)
                return dados.get('memoria', {})
        except:
            return {
                'interacoes': 0,
                'ultima_interacao': None,
                'preferencias': {},
                'conversas': deque(maxlen=50)
            }
    
    def mostrar_ajuda(self):
        ajuda = """
🔧 COMANDOS DO BENCH-VIS 4.0:

📁 PROJETOS:
  • "projeto novo NOME" - criar projeto
  • "listar projetos" - lista todos
  • "deletar projeto ID" - remove projeto (com confirmação)
  • "componentes do projeto ID" - lista componentes do projeto

🎨 IMAGENS:
  • "gerar imagem [descrição]" - cria imagem com IA e salva

💻 CÓDIGO:
  • "gerar codigo [descrição]" - gera código (Arduino, Python...)

🎭 ENTRETENIMENTO:
  • "fato" ou "curiosidade" - conta algo interessante
  • "conselho" - dá um conselho
  • "piada" - conta uma piada

🤖 IA:
  • "toggle ia" - liga/desliga o modo inteligente
  • Com IA ligada, pode conversar sobre qualquer assunto

🎤 MODOS:
  • "modo texto", "modo voz", "modo hibrido"
  • "sair" - encerra

💡 DICA: A personalidade muda com o tempo!
        """
        print(ajuda)
        self.falar("Comandos disponíveis no terminal.")
    
    def executar(self):
        print("\n🔧 Assistente 4.0 pronto! Use 'ajuda' para comandos.\n")
        
        def decaimento():
            while self.ativo:
                time.sleep(300)  # 5 minutos
                self.personalidade['energia'] = max(0, self.personalidade['energia'] - 5)
                self.personalidade['humor'] = max(0, self.personalidade['humor'] - 1)
        
        self.ativo = True
        threading.Thread(target=decaimento, daemon=True).start()
        
        while self.ativo:
            comando = None
            if self.modo_entrada == "voz":
                comando = self.ouvir_voz()
            elif self.modo_entrada == "texto":
                comando = self.ler_texto()
            else:  # hibrido
                comando = self.ouvir_voz()
                if comando is None:
                    comando = self.ler_texto()
            
            if comando:
                self.processar_comando(comando)
            
            time.sleep(0.1)
        
        print("\n👋 Até mais!")


if __name__ == "__main__":
    print("🚀 Inicializando BENCH-VIS 4.0...")
    # Teste rápido da API
    try:
        test = Pollinations()
        test.chat.completions.create(messages=[{"role":"user","content":"teste"}], model="openai", max_tokens=5)
        print("✅ API Pollinations conectada!")
    except Exception as e:
        print(f"⚠️ API Pollinations indisponível: {e}")
    
    assistente = AssistenteProMax(modo_entrada="hibrido")
    try:
        assistente.executar()
    except KeyboardInterrupt:
        print("\n\nEncerrando...")
        assistente.falar("Até mais!")
        assistente.salvar_memoria()
        assistente.conn.close()