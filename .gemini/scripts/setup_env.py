import os
import sys
from pathlib import Path

def load_dotenv(path):
    if not os.path.exists(path):
        return
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

def setup():
    # Load .env from current directory
    load_dotenv('.env')
    
    # Set AGENT_ROOT if not set
    if 'AGENT_ROOT' not in os.environ:
        os.environ['AGENT_ROOT'] = str(Path.cwd())
    
    # For sub-processes, we might want to return the env dict or just set it
    # But since we are likely running this in a python-based workflow runner,
    # setting it in os.environ is enough for this process.

if __name__ == "__main__":
    setup()
    print(f"AGENT_ROOT={os.environ['AGENT_ROOT']}")
    if 'TAVILY_API_KEY' in os.environ:
        print(f"TAVILY_API_KEY={os.environ['TAVILY_API_KEY'][:8]}...")
    if 'OBSIDIAN_VAULT_PATH' in os.environ:
        print(f"OBSIDIAN_VAULT_PATH={os.environ['OBSIDIAN_VAULT_PATH']}")
