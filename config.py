# config.py
import os # Importa o módulo os para acessar variáveis de ambiente
from dotenv import load_dotenv # Importa load_dotenv para carregar o .env
import json # Importa o módulo json para ler config.json

# Carrega as variáveis de ambiente do arquivo .env
# É importante que esta linha esteja aqui se você quiser que config.py use o .env
load_dotenv()

# Tenta carregar configurações do config.json como fallback
config_data = {}
try:
    with open('config.json', 'r') as f:
        config_data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    print("Warning: config.json not found or could not be decoded. Relying primarily on environment variables.")
    config_data = {} # Ensure config_data is an empty dict if file reading fails


# Seu token do bot do Discord. Mantenha-o seguro e não o compartilhe!
# Tenta ler da variável de ambiente DISCORD_BOT_TOKEN, fallback para config.json
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if DISCORD_BOT_TOKEN is None:
    DISCORD_BOT_TOKEN = config_data.get("DISCORD_BOT_TOKEN")
    if DISCORD_BOT_TOKEN is None:
        print("Error: DISCORD_BOT_TOKEN not found in environment variables or config.json")
        # Consider adding sys.exit(1) here if the token is mandatory


# Prefixo para comandos de texto (ex: !help, !ping)
# Tenta ler da variável de ambiente COMMAND_PREFIX, fallback para config.json, padrão '!'
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX")
if COMMAND_PREFIX is None:
    COMMAND_PREFIX = config_data.get("COMMAND_PREFIX", "!") # Fallback to JSON, with default '!' if not in JSON


# ID do seu servidor de testes (guild ID) para sincronização rápida de comandos de barra.
# Se você quiser que os comandos de barra sincronizem globalmente (pode levar até 1 hora),
# defina TEST_GUILD_ID como None no seu .env.
# Converte para int, se não for possível, define como None.
TEST_GUILD_ID = os.getenv("TEST_GUILD_ID")
if TEST_GUILD_ID:
    try:
        TEST_GUILD_ID = int(TEST_GUILD_ID)
    except ValueError:
        TEST_GUILD_ID = None

# ID da aplicação do seu bot (Application ID). Encontrado no Portal do Desenvolvedor do Discord.
# Converte para int, se não for possível, define como None.
DISCORD_BOT_APPLICATION_ID = os.getenv("DISCORD_BOT_APPLICATION_ID")
if DISCORD_BOT_APPLICATION_ID:
    try:
        DISCORD_BOT_APPLICATION_ID = int(DISCORD_BOT_APPLICATION_ID)
    except ValueError:
        DISCORD_BOT_APPLICATION_ID = None

# ID do proprietário do bot (seu ID de usuário do Discord)
# Usado para comandos restritos ao proprietário.
# Tenta ler da variável de ambiente OWNER_ID, fallback para config.json
OWNER_ID = os.getenv("OWNER_ID")
if OWNER_ID is None:
    OWNER_ID = config_data.get("OWNER_ID")

# Converte para int, se não for possível ou não encontrado, define como None.
if OWNER_ID:
    try:
        OWNER_ID = int(OWNER_ID)
    except ValueError:
        print(f"Warning: Invalid OWNER_ID '{OWNER_ID}' found in config. Converting to None.")
        OWNER_ID = None
else:
    # Handle the case where OWNER_ID was not found in env vars or config.json
    print("Warning: OWNER_ID not found in environment variables or config.json. Bot owner commands may not work.")
    OWNER_ID = None # Explicitly set to None if not found
