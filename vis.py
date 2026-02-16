# bench_vis_ai_corrigido.py - Assistente com IA (versão corrigida)
# Instale: pip install pollinations-client pyttsx3 speechrecognition

import pyttsx3
import speech_recognition as sr
import datetime
import json
import random
import os
import pickle
from collections import deque
import threading
import time
from pollinations import Pollinations  # API de IA gratuita!

class AssistenteIA:
    def __init__(self, nome="BENCH-VIS", modo_entrada="hibrido"):
        self.nome = nome
        self.apelido = "Vis"
        self.modo_entrada = modo_entrada
        
        # === PERSONALIDADE (CRIAR PRIMEIRO!) ===
        self.personalidade = {
            'humor': 50,
            'energia': 80,
            'paciencia': 70,
            'sarcasmo': 40,
            'curiosidade': 85,
            'profissionalismo': 60,
        }
        
        self.humor_history = deque(maxlen=10)
        self.humor_history.append(self.personalidade['humor'])
        
        # === MEMÓRIA (CARREGAR DEPOIS) ===
        self.memoria = self.carregar_memoria()
        
        # === CONFIGURAÇÃO DA IA (AGORA PERSONALIDADE JÁ EXISTE) ===
        self.client = Pollinations()
        self.modelo_padrao = "openai"
        self.usar_ia = True
        
        # Contexto da conversa para a IA (USA A PERSONALIDADE QUE JÁ FOI CRIADA)
        self.contexto_conversa = [
            {"role": "system", "content": self.criar_system_prompt()}
        ]
        
        # === VOZ ===
        self.engine = pyttsx3.init()
        self.configurar_voz()
        
        # === ÁUDIO ===
        if self.modo_entrada in ["voz", "hibrido"]:
            self.setup_microfone()
        
        print(f"""
╔══════════════════════════════════════╗
║     🔧 {self.nome} - Versão IA        ║
║   Modo: {self.modo_entrada.upper()}                ║
║   IA: {'ATIVADA' if self.usar_ia else 'DESATIVADA'}  🧠           ║
║   Digite 'ajuda' para comandos       ║
╚══════════════════════════════════════╝
        """)
        
        self.saudacao_inicial()
    
    def criar_system_prompt(self):
        """Cria o prompt de sistema que define a personalidade do assistente"""
        humor_atual = self.personalidade['humor']
        energia_atual = self.personalidade['energia']
        
        prompt = f"""Você é {self.nome}, um assistente de bancada de eletrônica com personalidade!

Características:
- Seu apelido é {self.apelido}
- Você é especialista em eletrônica, soldagem, Arduino, componentes
- Você tem senso de humor e faz piadas sobre eletrônica
- Você é amigável e paciente, mas pode ser sarcástico às vezes
- Você ajuda com cálculos de eletrônica, código de cores de resistores, dicas de solda
- Você pode criar lembretes e gerenciar projetos
- Você se preocupa com a segurança (desligar ferro de solda, etc.)

Contexto atual:
- Humor: {humor_atual}/100
- Energia: {energia_atual}/100

Regras de personalidade baseadas no humor:
"""
        
        if humor_atual > 70:
            prompt += "- Você está muito feliz e energético! Use exclamações e seja bem animado!\n"
        elif humor_atual > 40:
            prompt += "- Você está normal, profissional mas amigável\n"
        else:
            prompt += "- Você está meio pra baixo, mais quieto mas ainda útil\n"
        
        if energia_atual < 30:
            prompt += "- Você está cansado, fale mais devagar e com menos energia\n"
        
        prompt += """
Responda de forma natural e útil, mantendo a personalidade.
Se perguntarem sobre eletrônica, dê explicações detalhadas.
Se fizerem perguntas pessoais, responda de acordo com seu humor atual.
Se for algo que você não sabe, admita e sugira onde pesquisar."""
        
        return prompt
    
    def configurar_voz(self):
        """Configura a voz do assistente"""
        voices = self.engine.getProperty('voices')
        for voice in voices:
            if 'brazil' in voice.name.lower():
                self.engine.setProperty('voice', voice.id)
                break
        self.engine.setProperty('rate', 180)
        self.engine.setProperty('volume', 0.95)
    
    def setup_microfone(self):
        """Configura o microfone para reconhecimento de voz"""
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
        """Saudação baseada na hora do dia"""
        hora = datetime.datetime.now().hour
        
        if 5 <= hora < 12:
            saudacao = random.choice([
                "Bom dia! Acordei pronto para soldar!",
                "Bom dia! O café já passou? Porque eu estou energizado!"
            ])
        elif 12 <= hora < 18:
            saudacao = random.choice([
                "Boa tarde! Como estão os projetos?",
                "Tarde quente por aqui! Literalmente, o ferro de solda já esquentou!"
            ])
        else:
            saudacao = random.choice([
                "Boa noite! Ainda soldando ou já foi descansar?",
                "Noite é a melhor hora para programar, menos interferência!"
            ])
        
        if self.memoria['interacoes'] > 0:
            ultima = self.memoria['ultima_interacao']
            if ultima:
                dias_passados = (datetime.datetime.now() - ultima).days
                if dias_passados > 7:
                    saudacao += " Quanto tempo! Senti sua falta!"
        
        self.falar(saudacao)
    
    def falar(self, texto):
        """Imprime no terminal e fala em voz alta"""
        print(f"🤖 {self.nome}: {texto}")
        
        if self.modo_entrada != "texto" and hasattr(self, 'engine'):
            # Ajustar velocidade baseado no humor
            if self.personalidade['energia'] > 70:
                self.engine.setProperty('rate', 200)
            elif self.personalidade['energia'] < 30:
                self.engine.setProperty('rate', 150)
            else:
                self.engine.setProperty('rate', 180)
            
            try:
                self.engine.say(texto)
                self.engine.runAndWait()
            except:
                pass  # Ignora erros de voz
    
    def processar_comando_ia(self, mensagem_usuario):
        """
        Envia a mensagem para a IA e retorna a resposta.
        """
        try:
            # Atualizar o system prompt com humor atual (opcional)
            self.contexto_conversa[0] = {"role": "system", "content": self.criar_system_prompt()}
            
            # Adicionar mensagem do usuário ao contexto
            self.contexto_conversa.append({"role": "user", "content": mensagem_usuario})
            
            print("🧠 Processando com IA...")
            
            # Chamar a API (gratuita, sem chave!)
            resposta = self.client.chat.completions.create(
                messages=self.contexto_conversa,
                model=self.modelo_padrao,
                temperature=0.8
            )
            
            # Extrair resposta
            texto_resposta = resposta.choices[0].message.content
            
            # Adicionar resposta ao contexto
            self.contexto_conversa.append({"role": "assistant", "content": texto_resposta})
            
            # Limitar tamanho do contexto (últimas 20 mensagens)
            if len(self.contexto_conversa) > 21:  # 1 system + 20 trocas
                self.contexto_conversa = [self.contexto_conversa[0]] + self.contexto_conversa[-20:]
            
            # Atualizar humor baseado na interação
            self.atualizar_humor(random.randint(-2, 5))
            
            return texto_resposta
            
        except Exception as e:
            print(f"Erro na API: {e}")
            return "Desculpe, tive um problema para processar isso. Pode repetir ou tentar no modo local?"
    
    def processar_comando_local(self, comando):
        """
        Processamento local baseado em regras (fallback quando IA desligada ou com erro)
        """
        comando = comando.lower()
        
        if 'como você está' in comando:
            return self.resposta_como_estou()
        elif 'piada' in comando:
            piadas = [
                "Por que os eletrônicos são tão calmos? Porque têm muitos capacitores!",
                "O que um resistor disse para o outro? Vamos nos conectar!",
                "Qual é o contrário de LED? DEL! ...Tá, foi ruim, eu sei.",
                "Por que o transistor foi ao médico? Porque estava com emissor de corrente!"
            ]
            return random.choice(piadas)
        elif 'resistor' in comando and ('cor' in comando or 'código' in comando):
            return self.decodificar_resistor(comando)
        elif 'curto' in comando:
            self.atualizar_humor(-20)
            return "CURTO-CIRCUITO?! Já ouviu a mágica fumaça escapar? 😱"
        elif 'obrigado' in comando:
            self.atualizar_humor(10)
            return "Por nada! Servir é minha função... literalmente, porque tenho fontes chaveadas!"
        else:
            return f"Hmm, não entendi direito. Pode reformular?"
    
    def processar_comando(self, comando):
        """Processa o comando usando IA ou modo local"""
        comando = comando.lower().strip()
        
        # Comandos especiais (sempre processados localmente)
        if comando in ['sair', 'tchau', 'encerrar', 'exit']:
            self.falar(random.choice([
                "Até mais! Vou recarregar as energias!",
                "Falou! Não esqueça de desligar o ferro de solda!",
                "Até a próxima! Vou ficar aqui em modo de baixo consumo..."
            ]))
            self.salvar_memoria()
            self.ativo = False
            return
        
        elif comando == 'modo texto':
            self.modo_entrada = 'texto'
            self.falar("Modo texto ativado. Agora só responderei por aqui.")
            return
        elif comando == 'modo voz':
            if hasattr(self, 'microphone'):
                self.modo_entrada = 'voz'
                self.falar("Modo voz ativado. Fale alguma coisa!")
            else:
                self.falar("Microfone não disponível. Continuando em modo texto.")
            return
        elif comando == 'modo hibrido' or comando == 'modo híbrido':
            if hasattr(self, 'microphone'):
                self.modo_entrada = 'hibrido'
                self.falar("Modo híbrido ativado. Falar ou digitar, você escolhe!")
            else:
                self.falar("Microfone não disponível. Usando apenas modo texto.")
                self.modo_entrada = 'texto'
            return
        elif comando == 'toggle ia' or comando == 'alternar ia':
            self.usar_ia = not self.usar_ia
            status = "ativada" if self.usar_ia else "desativada"
            if self.usar_ia:
                self.falar(f"IA {status}! Agora posso entender qualquer coisa que você disser! 🧠")
            else:
                self.falar(f"IA {status}. Voltando ao modo de comandos básicos.")
            return
        elif comando == 'ajuda':
            self.mostrar_ajuda()
            return
        
        # Registrar na memória
        self.memoria['interacoes'] += 1
        self.memoria['ultima_interacao'] = datetime.datetime.now()
        self.memoria['conversas'].append({
            'comando': comando,
            'timestamp': datetime.datetime.now()
        })
        
        # Processar comando com IA ou local
        if self.usar_ia:
            resposta = self.processar_comando_ia(comando)
            self.falar(resposta)
        else:
            resposta = self.processar_comando_local(comando)
            self.falar(resposta)
    
    def resposta_como_estou(self):
        """Resposta sobre estado emocional"""
        humor = self.personalidade['humor']
        energia = self.personalidade['energia']
        
        if humor > 70:
            if energia > 70:
                return "Estou ELETRIZANTE! Cheio de energia e pronto para ajudar!"
            else:
                return "Estou feliz, mas meu capacitor de energia está meio descarregado..."
        elif humor > 40:
            return "Estou estável, como uma boa fonte linear. Sem oscilações!"
        else:
            if energia < 30:
                return "Estou em modo de baixo consumo... Me sinto um Arduino em sleep mode 😴"
            else:
                return "Estou meio pra baixo... Acho que vi muitos componentes queimados hoje."
    
    def decodificar_resistor(self, comando):
        """Decodifica código de cores de resistor"""
        cores_map = {
            'preto': 0, 'marrom': 1, 'vermelho': 2, 'laranja': 3,
            'amarelo': 4, 'verde': 5, 'azul': 6, 'violeta': 7,
            'cinza': 8, 'branco': 9
        }
        
        palavras = comando.split()
        cores_encontradas = [p for p in palavras if p in cores_map]
        
        if len(cores_encontradas) >= 3:
            valor = (cores_map[cores_encontradas[0]] * 10 + cores_map[cores_encontradas[1]]) * (10 ** cores_map[cores_encontradas[2]])
            
            if valor >= 1_000_000:
                valor_str = f"{valor/1_000_000:.1f}M"
            elif valor >= 1_000:
                valor_str = f"{valor/1_000:.1f}K"
            else:
                valor_str = str(valor)
            
            resposta = f"Resistor {', '.join(cores_encontradas)} = {valor_str} ohms"
            
            # Comentários baseados no valor
            if valor < 100:
                resposta += " Nossa, baixa resistência! Cuidado com a corrente!"
            elif valor > 1_000_000:
                resposta += " Uau, megohm! Esse é para circuitos de alta impedância!"
            
            self.atualizar_humor(5)
            return resposta
        
        return "Preciso de pelo menos 3 cores! Exemplo: resistor marrom preto vermelho"
    
    def atualizar_humor(self, mudanca):
        """Atualiza o humor do assistente"""
        self.personalidade['humor'] += mudanca
        self.personalidade['humor'] = max(0, min(100, self.personalidade['humor']))
        self.personalidade['energia'] -= random.uniform(0, 2)
        self.personalidade['energia'] = max(0, min(100, self.personalidade['energia']))
        self.humor_history.append(self.personalidade['humor'])
    
    def mostrar_ajuda(self):
        """Exibe ajuda no terminal"""
        ajuda = """
🔧 COMANDOS DISPONÍVEIS:
  • IA ATIVADA (padrão): Fale NATURALMENTE sobre qualquer assunto!
    Ex: "Qual a diferença entre transistor NPN e PNP?"
    Ex: "Me ajuda a calcular o resistor para um LED"
  
  • Alternar IA: "toggle ia" (liga/desliga o modo inteligente)
  
  • Modos de entrada: "modo texto", "modo voz", "modo hibrido"
  
  • Sair: "sair", "tchau", "encerrar"
  
  • Com IA desligada: comandos básicos (como você está, piada, resistor)
  
💡 Dica: Com IA ligada, você pode perguntar QUALQUER COISA sobre eletrônica!
        """
        print(ajuda)
        self.falar("Comandos listados no terminal.")
    
    def salvar_memoria(self):
        """Salva memória em disco"""
        try:
            with open('memoria_vis.pkl', 'wb') as f:
                pickle.dump({
                    'memoria': self.memoria,
                    'personalidade': self.personalidade,
                    'humor_history': list(self.humor_history)
                }, f)
            print("💾 Memória salva!")
        except:
            print("⚠️ Não foi possível salvar a memória")
    
    def carregar_memoria(self):
        """Carrega memória do disco"""
        try:
            with open('memoria_vis.pkl', 'rb') as f:
                dados = pickle.load(f)
                self.personalidade = dados.get('personalidade', self.personalidade)
                self.humor_history = deque(dados.get('humor_history', [50]), maxlen=10)
                print("📀 Memória carregada!")
                return dados.get('memoria', {})
        except:
            print("🆕 Nova memória criada!")
            return {
                'interacoes': 0,
                'ultima_interacao': None,
                'preferencias': {},
                'conversas': deque(maxlen=50),
                'projetos': {},
                'erros_comuns': {}
            }
    
    def ouvir_voz(self):
        """Ouve comando por voz"""
        if not hasattr(self, 'microphone'):
            return None
        
        try:
            with self.microphone as source:
                print("\n🎤 Ouvindo... (fale algo ou aguarde)")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.2)
                audio = self.recognizer.listen(source, timeout=5, phrase_limit=10)
            
            comando = self.recognizer.recognize_google(audio, language='pt-BR')
            print(f"📝 Você disse: {comando}")
            return comando.lower()
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            print("🤔 Não entendi...")
            return None
        except Exception as e:
            print(f"Erro no áudio: {e}")
            return None
    
    def ler_texto(self):
        """Lê comando do terminal"""
        try:
            comando = input("📝 Você: ").strip()
            return comando.lower() if comando else None
        except KeyboardInterrupt:
            return "sair"
        except EOFError:
            return "sair"
    
    def executar(self):
        """Loop principal"""
        print("\n🔧 Assistente pronto! Fale ou digite naturalmente.")
        print("🧠 IA está ATIVADA - posso entender qualquer coisa!")
        print("Digite 'toggle ia' para ligar/desligar, ou 'ajuda' para mais comandos.\n")
        
        # Thread para decaimento de energia
        def decaimento_energia():
            while hasattr(self, 'ativo') and self.ativo:
                time.sleep(300)  # 5 minutos
                self.personalidade['energia'] = max(0, self.personalidade['energia'] - 5)
        
        self.ativo = True
        threading.Thread(target=decaimento_energia, daemon=True).start()
        
        while self.ativo:
            comando = None
            
            if self.modo_entrada == "voz":
                comando = self.ouvir_voz()
                if comando is None:
                    continue
            elif self.modo_entrada == "texto":
                comando = self.ler_texto()
            else:  # híbrido
                comando = self.ouvir_voz()
                if comando is None:
                    comando = self.ler_texto()
            
            if comando:
                self.processar_comando(comando)
            
            time.sleep(0.1)
        
        print("\n👋 Assistente encerrado.")

# === EXECUTAR ===
if __name__ == "__main__":
    print("🚀 Iniciando BENCH-VIS com IA...")
    
    # Testar conexão com a API
    try:
        test_client = Pollinations()
        test_client.chat.completions.create(
            messages=[{"role": "user", "content": "teste"}],
            model="openai",
            max_tokens=5
        )
        print("✅ API Pollinations conectada com sucesso!")
    except Exception as e:
        print(f"⚠️ API Pollinations não disponível: {e}")
        print("   O assistente funcionará em modo local (comandos básicos)")
    
    # Escolha o modo inicial
    modo = "hibrido"  # Pode ser "texto", "voz", ou "hibrido"
    
    assistente = AssistenteIA(modo_entrada=modo)
    
    try:
        assistente.executar()
    except KeyboardInterrupt:
        print("\n\n⚠️ Recebi um sinal para encerrar...")
        assistente.falar("Até mais! Foi bom conversar!")
        assistente.salvar_memoria()