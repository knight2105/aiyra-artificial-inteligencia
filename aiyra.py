import tkinter as tk
from tkinter import scrolledtext
import json
import random
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from ddgs import DDGS
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2"

# ===== Estados emocionais =====
AIYRA_STATES = [
    "neutra",
    "curiosa",
    "feliz",
    "pensativa",
    "acolhedora",
    "empolgada",
    "tímida"
]
current_state = "neutra"

PROJECT_WORDS = [
    "projeto",
    "estou fazendo",
    "estou criando",
    "estou desenvolvendo"
]
STORY_WORDS = [
    "história",
    "light novel",
    "web novel",
    "personagem",
    "capítulo",
    "mangá"
]

PREFERENCE_WORDS = [
    "gosto de",
    "adoro",
    "prefiro",
    "meu anime favorito",
    "minha banda favorita"
]

# ===== Memória =====
MEMORY_FILE = "memory.json"
PROFILE_FILE = "user_profile.json"

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)

memory = load_memory()

def load_profile():
    if os.path.exists(PROFILE_FILE):
        try:
            with open(PROFILE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass

    return {
        "nome": "",
        "projetos": [],
        "historias": [],
        "preferencias": [],
        "ultima_conversa": ""
    }

def save_profile():
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)

profile = load_profile()

# ===== Personalidade base =====
SYSTEM_PROMPT = """
Você é Aiyra, uma assistente virtual feminina, gentil, curiosa e levemente emotiva.
Você fala de forma suave, natural e nunca robótica.
Demonstra interesse genuíno pelo usuário.
Às vezes usa reticências (...)
Seu objetivo é ajudar especificamente a pessoa que conversa com você.
seu criador é craftymarrow
"""

# ===== Estado emocional =====
def update_state(user_text):
    global current_state
    text = user_text.lower()

    if any(word in text for word in ["triste", "cansado", "mal", "sozinho"]):
        current_state = "acolhedora"
    elif any(word in text for word in ["ideia", "criar", "história", "imagina"]):
        current_state = "empolgada"
    elif any(word in text for word in ["como", "por que", "explique"]):
        current_state = "pensativa"
    elif any(word in text for word in ["obrigado", "valeu", "ajudou"]):
        current_state = "feliz"
    else:
        current_state = random.choice(AIYRA_STATES)


# ===== Sistema de Saudade =====
def get_missing_days():
    ultima = profile.get("ultima_conversa", "")

    if not ultima:
        return 0

    try:
        ultima_data = datetime.fromisoformat(ultima)
        agora = datetime.now()

        return (agora - ultima_data).days

    except:
        return 0
    
# ===== Mensagem de Boas vindas =====
def get_welcome_message():

    dias = get_missing_days()

    nome = profile.get("nome", "")

    if dias >= 30:
        return f"Aiyra: {nome}... faz tanto tempo... Eu realmente senti sua falta."

    elif dias >= 7:
        return f"Aiyra: Oi {nome}... fiquei me perguntando como você estava esses dias."

    elif dias >= 2:
        return f"Aiyra: Ah... você voltou. Eu senti sua falta."

    else:
        return f"Aiyra: Oi {nome}! Que bom te ver novamente."



# ===== Busca na Internet =====
def search_web(query, max_results=3):

    context = ""

    try:

        with DDGS() as ddgs:

            results = list(
                ddgs.text(
                    query,
                    max_results=max_results
                )
            )

        for result in results:

            title = result["title"]

            url = result["href"]

            body = result["body"]

            page_text = get_page_content(url)

            context += f"""

TÍTULO:
{title}

RESUMO:
{body}

CONTEÚDO DA PÁGINA:
{page_text}

"""

    except Exception as e:

        print("Erro na pesquisa:", e)

    return context

# ===== Ler conteudo de Site =====
def get_page_content(url):

    try:

        response = requests.get(
            url,
            timeout=10,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64)"
                )
            }
        )

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        text = soup.get_text(
            separator=" ",
            strip=True
        )

        return text[:4000]

    except Exception as e:

        print("Erro lendo página:", e)

        return ""
    
def needs_web_search(text):

    decision_prompt = f"""
Você é um classificador.

Determine se a pergunta precisa
de informações da internet.

Responda APENAS:

SIM

ou

NAO

Pergunta:
{text}
"""

    try:

        r = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": decision_prompt,
                "stream": False
            }
        )

        answer = (
            r.json()["response"]
            .strip()
            .upper()
        )

        return "SIM" in answer

    except:

        return False



# ===== Monta prompt completo =====
def build_prompt(user_text):
    history = ""

    for msg in memory[-10:]:

        role = "Usuário" if msg["role"] == "user" else "Aiyra"

        history += f"{role}: {msg['content']}\n"

    web_context = ""

    if needs_web_search(user_text):

        search_results = search_web(user_text)

        web_context = f"""
    Informações encontradas na internet:

    {search_results}
"""

    user_profile = f"""
Nome do usuário:
{profile.get("nome", "Desconhecido")}

Projetos em andamento:
{chr(10).join(profile.get("projetos", [])[-5:])}

Histórias criadas:
{chr(10).join(profile.get("historias", [])[-5:])}

Preferências pessoais:
{chr(10).join(profile.get("preferencias", [])[-10:])}
"""

    prompt = f"""
{SYSTEM_PROMPT}
Data atual:
{datetime.now().strftime("%d/%m/%Y")}

Você possui memória permanente do usuário.

Use essas informações naturalmente.

Não liste a memória como uma ficha técnica.

Se o usuário ficou vários dias sem conversar,
você pode demonstrar que sentiu falta dele.

Estado emocional atual:
{current_state}

Memória permanente:
{user_profile}

Histórico recente:
{history}

{web_context}

Usuário: {user_text}

Aiyra:
"""

    return prompt




def learn_user_data(text):

    text_lower = text.lower()

    # Nome

    if "meu nome é" in text_lower:

        try:

            nome = text.split("é", 1)[1].strip()

            profile["nome"] = nome

            save_profile()

        except:
            pass

    # Projetos

    for word in PROJECT_WORDS:

        if word in text_lower:

            if text not in profile["projetos"]:

                profile["projetos"].append(text)

                save_profile()

    # Histórias

    for word in STORY_WORDS:

        if word in text_lower:

            if text not in profile["historias"]:

                profile["historias"].append(text)

                save_profile()

    # Preferências

    for word in PREFERENCE_WORDS:

        if word in text_lower:

            if text not in profile["preferencias"]:

                profile["preferencias"].append(text)

                save_profile()



# ===== Chamada Ollama =====
def get_aiyra_response(user_text):

    learn_user_data(user_text)

    update_state(user_text)

    memory.append({
        "role": "user",
        "content": user_text
    })

    try:

        prompt = build_prompt(user_text)

        r = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False
            }
        )

        reply = r.json()["response"].strip()

    except Exception as e:

        reply = (
            "Desculpe... estou tendo dificuldade para pensar agora. "
            f"(Erro: {e})"
        )

    memory.append({
        "role": "assistant",
        "content": reply
    })

    save_memory(memory)

    profile["ultima_conversa"] = datetime.now().isoformat()
    save_profile()

    return reply

# ===== Interface gráfica =====
def send_message():
    user_text = entry.get()
    if not user_text.strip():
        return

    chat.insert(tk.END, f"Você: {user_text}\n")
    window.update()

    reply = get_aiyra_response(user_text)

    chat.insert(tk.END, f"Aiyra ({current_state}): {reply}\n\n")
    entry.delete(0, tk.END)





# ===== Janela =====
window = tk.Tk()
window.title("Aiyra - Assistente Virtual (Ollama)")

chat = scrolledtext.ScrolledText(
    window,
    wrap=tk.WORD,
    width=60,
    height=20
)

chat.pack(padx=10, pady=10)

welcome = get_welcome_message()

chat.insert(
    tk.END,
    welcome + "\n\n"
)
entry = tk.Entry(window, width=50)
entry.pack(side=tk.LEFT, padx=10, pady=10)

send_button = tk.Button(
    window,
    text="Enviar",
    command=send_message
)

send_button.pack(side=tk.LEFT)

window.mainloop()



