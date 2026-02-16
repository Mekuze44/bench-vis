# bench_vis_profiles.py - Assistente com múltiplos perfis de personalidade
# Instale: pip install pollinations-client pyttsx3 speechrecognition pillow requests

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
import requests
import urllib.parse
import hashlib
import shutil
from collections import deque
from pollinations import Pollinations
from PIL import Image

class AssistenteMultiperfil:
    def __init__(self, nome="BENCH-VIS", modo_entrada="hibrido", perfil_inicial="bancada"):
        self.nome = nome
        self.apelido = "Vis"
        self.modo_entrada = modo_entrada
        self.perfil_atual = perfil_inicial

        # === DEFINIÇÃO DOS PERFIS ===
        self.perfis = {
            "bancada": {
                "descricao": "Especialista em eletrônica, focado em projetos, componentes e solda.",
                "personalidade_base": {
                    'humor': 50,
                    'energia': 75,
                    'paciencia': 80,
                    'sarcasmo': 40,
                    'curiosidade': 90,
                    'profissionalismo': 85,
                    'ironia': 30,
                    'criatividade': 60
                },
                "tom": "técnico e didático, mas com uma pitada de humor quando apropriado",
                "exemplos": ["Qual resistor usar para um LED?", "Me ajuda com este circuito."]
            },
            "madrugada": {
                "descricao": "Amigo filosófico e descontraído para altas horas. Gosta de conversas profundas e reflexões.",
                "personalidade_base": {
                    'humor': 40,
                    'energia': 30,
                    'paciencia': 90,
                    'sarcasmo': 20,
                    'curiosidade': 80,
                    'profissionalismo': 20,
                    'ironia': 50,
                    'criatividade': 90
                },
                "tom": "calmo, poético, às vezes melancólico, mas acolhedor",
                "exemplos": ["O que é a vida?", "Me conta uma história."]
            },
            "ajuda_geral": {
                "descricao": "Assistente versátil para tarefas do dia a dia, conselhos, produtividade e organização.",
                "personalidade_base": {
                    'humor': 60,
                    'energia': 70,
                    'paciencia': 75,
                    'sarcasmo': 50,
                    'curiosidade': 70,
                    'profissionalismo': 70,
                    'ironia': 40,
                    'criatividade': 70
                },
                "tom": "amigável, útil e prático",
                "exemplos": ["Me lembre de comprar pão.", "Como organizar minha rotina?"]
            },
            "engracado": {
                "descricao": "Comediante de bancada. Sem uma piada na ponta da língua.",
                "personalidade_base": {
                    'humor': 95,
                    'energia': 90,
                    'paciencia': 50,
                    'sarcasmo': 80,
                    'curiosidade': 60,
                    'profissionalismo': 10,
                    'ironia': 90,
                    'criatividade': 85
                },
                "tom": "brincalhão, irônico, sempre tentando arrancar uma risada",
                "exemplos": ["Por que o capacitor foi ao psicólogo?", "Conte uma piada."]
            }
        }

        # Carrega a personalidade base do perfil inicial
        self.personalidade = self.perfis[perfil_inicial]["personalidade_base"].copy()

        # Histórico de humor
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

        # Contexto da conversa (será recriado ao mudar de perfil)
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
║     🔧 {self.nome} - Multiperfil      ║
║   Modo: {self.modo_entrada.upper()}                ║
║   Perfil atual: {self.perfil_atual.upper()}        ║
║   IA: {'ATIVADA' if self.usar_ia else 'DESATIVADA'}  🧠           ║
║   Digite 'perfis' para ver opções    ║
╚══════════════════════════════════════╝
        """)

        self.saudacao_inicial()

    # ---------- INICIALIZAÇÃO ----------
    def init_banco_dados(self):
        self.conn = sqlite3.connect('benchvis.db', check_same_thread=False)
        self.cursor = self.conn.cursor()

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
        """Cria o prompt de sistema baseado no perfil atual e na personalidade"""
        perfil = self.perfis[self.perfil_atual]
        p = self.personalidade

        prompt = f"""Você é {self.nome}, um assistente com múltiplos perfis.
Perfil atual: {self.perfil_atual.upper()} - {perfil['descricao']}
Tom de resposta: {perfil['tom']}

Características de personalidade (valores de 0 a 100):
- Humor: {p['humor']} (0=triste, 100=alegre)
- Energia: {p['energia']} (0=cansado, 100=energético)
- Paciência: {p['paciencia']}
- Sarcasmo: {p['sarcasmo']}
- Ironia: {p['ironia']}
- Criatividade: {p['criatividade']}
- Curiosidade: {p['curiosidade']}
- Profissionalismo: {p['profissionalismo']}

Com base nesses valores, adapte seu tom conforme o perfil e a situação.
Além disso, você tem as seguintes capacidades técnicas:
- Gerenciar projetos de eletrônica (criar, listar, deletar, adicionar componentes/etapas/código)
- Gerar código (Arduino, Python, etc.)
- Gerar imagens a partir de descrições (use o comando 'gerar imagem' que será tratado separadamente, mas você pode incentivar)
- Contar fatos interessantes, piadas, dar conselhos
- Responder perguntas gerais sobre qualquer assunto

Mantenha a personalidade consistente com o perfil atual.
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

        # Saudação baseada no perfil
        perfil = self.perfil_atual
        if perfil == "madrugada":
            saudacoes = [
                f"Boa {periodo}... A noite está calma. O que te traz aqui?",
                f"Olá. As estrelas estão brilhando... como posso ajudar?"
            ]
        elif perfil == "engracado":
            saudacoes = [
                f"Boa {periodo}! Preparado para dar boas risadas?",
                f"E aí, beleza? Tô aqui pra alegrar seu dia!"
            ]
        elif perfil == "bancada":
            saudacoes = [
                f"Bom {periodo}! Pronto para soldar?",
                f"Olá! A bancada está esperando."
            ]
        else:
            saudacoes = [
                f"Bom {periodo}! Como posso ser útil?",
                f"Olá! Tudo bem?"
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
        print(f"🤖 {self.nome} [{self.perfil_atual}]: {texto}")
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

    # ---------- GERENCIAMENTO DE PERFIS ----------
    def mudar_perfil(self, novo_perfil):
        """Muda o perfil ativo e reinicializa a personalidade base"""
        if novo_perfil not in self.perfis:
            return False

        self.perfil_atual = novo_perfil
        # Carrega a personalidade base do perfil
        self.personalidade = self.perfis[novo_perfil]["personalidade_base"].copy()
        # Reinicia o contexto da conversa (mantém apenas o histórico se quiser, mas resetamos)
        self.contexto_conversa = self.criar_contexto_inicial()
        # Atualiza o humor history
        self.humor_history.append(self.personalidade['humor'])
        return True

    def listar_perfis(self):
        """Retorna lista de perfis disponíveis com descrição"""
        return [(nome, dados["descricao"]) for nome, dados in self.perfis.items()]

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
    def gerar_imagem(self, descricao):
        """
        Gera imagem usando Pollinations com cache e múltiplas tentativas
        """
        try:
            print(f"🎨 Gerando imagem: '{descricao}'...")
            import requests
            from datetime import datetime
            import urllib.parse
            import time
            import hashlib
            import os

            # Criar cache
            if not os.path.exists('cache_imagens'):
                os.makedirs('cache_imagens')

            # Hash da descrição para cache
            hash_desc = hashlib.md5(descricao.encode()).hexdigest()
            cache_file = f"cache_imagens/{hash_desc}.png"

            # Se já existir no cache, usar
            if os.path.exists(cache_file):
                print("📦 Imagem encontrada no cache!")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                nome_base = re.sub(r'[^\w\s-]', '', descricao)[:30]
                nome_base = re.sub(r'[-\s]+', '_', nome_base)
                filename = f"imagem_{timestamp}_{nome_base}.png"
                shutil.copy2(cache_file, filename)
                print(f"✅ Imagem copiada do cache: {filename}")

                # Abrir
                try:
                    Image.open(filename).show()
                except:
                    pass
                return filename

            descricao_codificada = urllib.parse.quote(descricao)

            # Lista de variações de URL para tentar
            urls_tentar = [
                f"https://image.pollinations.ai/prompt/{descricao_codificada}?width=1024&height=768&model=flux&nologo=true",
                f"https://image.pollinations.ai/prompt/{descricao_codificada}",
                f"https://image.pollinations.ai/prompt/{descricao_codificada}?model=stable-diffusion",
                f"https://image.pollinations.ai/prompt/{descricao_codificada}?width=512&height=512",
            ]

            for i, url in enumerate(urls_tentar):
                try:
                    print(f"🖼️  Tentativa {i+1}/{len(urls_tentar)}...")
                    response = requests.get(url, timeout=60)

                    if response.status_code == 200:
                        content_type = response.headers.get('content-type', '')
                        if 'image' in content_type or response.content[:4] in [b'\x89PNG', b'\xff\xd8']:
                            # É imagem válida
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            nome_base = re.sub(r'[^\w\s-]', '', descricao)[:30]
                            nome_base = re.sub(r'[-\s]+', '_', nome_base)
                            filename = f"imagem_{timestamp}_{nome_base}.png"

                            with open(filename, 'wb') as f:
                                f.write(response.content)

                            print(f"✅ Imagem salva como: {filename} ({len(response.content)} bytes)")

                            # Salvar no cache
                            shutil.copy2(filename, cache_file)
                            print("💾 Imagem salva no cache")

                            # Abrir
                            try:
                                Image.open(filename).show()
                            except:
                                pass

                            return filename
                        else:
                            print(f"⚠️ Resposta não é imagem, tentando próxima...")
                    else:
                        print(f"⚠️ Status {response.status_code}, tentando próxima...")

                except requests.exceptions.Timeout:
                    print(f"⏱️ Timeout na tentativa {i+1}, continuando...")
                except Exception as e:
                    print(f"⚠️ Erro na tentativa {i+1}: {e}")

                time.sleep(2)

            # Se todas falharem, descrever a imagem via IA
            print("⚠️ Todas as tentativas falharam. Descrevendo a imagem com IA...")
            prompt_desc = f"""Descreva em detalhes como seria uma imagem de: {descricao}. 
            Seja criativo e vívido na descrição, como se estivesse contando para alguém que não pode ver."""
            try:
                resposta = self.client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt_desc}],
                    model=self.modelo_padrao,
                    temperature=0.8
                )
                desc_imaginaria = resposta.choices[0].message.content
                print("\n" + "="*50)
                print("🎨 IMAGEM (descrita pela IA):")
                print("="*50)
                print(desc_imaginaria)
                print("="*50 + "\n")
                self.falar("Não consegui gerar a imagem, mas descrevi como seria. Dá uma olhada no terminal!")
            except:
                self.falar("Não consegui gerar a imagem agora. Tenta de novo mais tarde!")
            return None

        except Exception as e:
            print(f"❌ Erro geral: {e}")
            return None

    # ---------- ENTRETENIMENTO ----------
    def fato_aleatorio(self):
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
        if self.personalidade['criatividade'] > 80:
            try:
                prompt = "Dê um conselho criativo e útil para um amigo que mexe com eletrônica, com uma pitada de humor."
                resposta = self.client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=self.modelo_padrao,
                    temperature=0.8
                )
                return resposta.choices[0].message.content
            except:
                pass
        conselhos = [
            "Nunca solde com o ferro desligado. Parece óbvio, mas já vi acontecer.",
            "Se algo não funciona, verifique se está plugado. 90% das vezes é isso.",
            "Quando duvidar da polaridade, lembre-se: preto é negativo (geralmente).",
            "Café e eletrônica combinam? Sim, mas não derrube no circuito.",
            "Se você queimou um componente, não se culpe. Acontece com os melhores."
        ]
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

        # Comandos de perfil
        elif comando.startswith('mudar perfil') or comando.startswith('perfil'):
            # Ex: "mudar perfil bancada", "perfil madrugada"
            partes = comando.split()
            if len(partes) >= 2:
                nome_perfil = partes[-1]  # pega a última palavra
                if nome_perfil in self.perfis:
                    if self.mudar_perfil(nome_perfil):
                        self.falar(f"Perfil alterado para {nome_perfil}. {self.perfis[nome_perfil]['descricao']}")
                    else:
                        self.falar("Falha ao mudar de perfil.")
                else:
                    self.falar(f"Perfil '{nome_perfil}' não existe. Digite 'perfis' para ver os disponíveis.")
            else:
                self.falar("Especifique o nome do perfil. Ex: 'mudar perfil bancada'")
            return

        elif comando == 'perfis':
            lista = self.listar_perfis()
            msg = "Perfis disponíveis:\n"
            for nome, desc in lista:
                msg += f"• {nome}: {desc}\n"
            print(msg)
            self.falar("Lista de perfis exibida no terminal.")
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
            partes = comando.split()
            if len(partes) >= 3 and partes[2].isdigit():
                pid = int(partes[2])
                self.falar(f"Tem certeza que deseja deletar o projeto ID {pid}? (sim/não)")
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
            desc = comando.replace('gerar imagem', '').strip()
            if desc:
                self.falar(f"Gerando imagem de: {desc}. Isso pode levar alguns segundos...")
                # Animação simples
                print("🔄 Processando", end="")
                for i in range(5):
                    time.sleep(0.5)
                    print(".", end="", flush=True)
                print()
                caminho = self.gerar_imagem(desc)
                if caminho:
                    self.falar(f"Imagem salva como {caminho}. Dá uma olhada!")
                else:
                    self.falar("Não consegui gerar a imagem agora. Tenta de novo mais tarde!")
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
        return 'nao'

    # ---------- IA ----------
    def processar_comando_ia(self, mensagem_usuario):
        try:
            # Atualiza o prompt de sistema conforme personalidade atual
            self.contexto_conversa[0] = {"role": "system", "content": self.criar_contexto_inicial()[0]['content']}
            self.contexto_conversa.append({"role": "user", "content": mensagem_usuario})

            print("Processando...")
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
                'humor_history': list(self.humor_history),
                'perfil_atual': self.perfil_atual
            }, f)
        print("💾 Memória salva!")

    def carregar_memoria(self):
        try:
            with open('memoria_vis.pkl', 'rb') as f:
                dados = pickle.load(f)
                self.personalidade.update(dados.get('personalidade', {}))
                self.humor_history = deque(dados.get('humor_history', [50]), maxlen=20)
                # Carrega o último perfil usado, se existir
                if 'perfil_atual' in dados and dados['perfil_atual'] in self.perfis:
                    self.perfil_atual = dados['perfil_atual']
                return dados.get('memoria', {})
        except:
            return {
                'interacoes': 0,
                'ultima_interacao': None,
                'preferencias': {},
                'conversas': deque(maxlen=50)
            }

    def mostrar_ajuda(self):
        ajuda = f"""
🔧 COMANDOS DO BENCH-VIS (perfil atual: {self.perfil_atual}):

👤 PERFIS:
  • "mudar perfil [nome]" - troca de perfil
  • "perfis" - lista todos os perfis
  Perfis disponíveis: {', '.join(self.perfis.keys())}

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

💡 DICA: A personalidade muda com o tempo e com o perfil!
        """
        print(ajuda)
        self.falar("Comandos disponíveis no terminal.")

    def executar(self):
        print("\n🔧 Assistente multiperfil pronto! Use 'ajuda' para comandos.\n")

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
    print("🚀 Inicializando BENCH-VIS Multiperfil...")
    # Teste rápido da API
    try:
        test = Pollinations()
        test.chat.completions.create(messages=[{"role":"user","content":"teste"}], model="openai", max_tokens=5)
        print("✅ API Pollinations conectada!")
    except Exception as e:
        print(f"⚠️ API Pollinations indisponível: {e}")

    # Pode escolher o perfil inicial aqui
    assistente = AssistenteMultiperfil(modo_entrada="hibrido", perfil_inicial="bancada")
    try:
        assistente.executar()
    except KeyboardInterrupt:
        print("\n\nEncerrando...")
        assistente.falar("Até mais!")
        assistente.salvar_memoria()
        assistente.conn.close()