import os
import yaml
import logging
from pathlib import Path

def load_config():
    repo_root = Path(__file__).resolve().parents[2]
    config_path = repo_root / "papers" / "config.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def setup_logging():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def get_api_key_from_env():
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        logging.error("DEEPSEEK_API_KEY environment variable not set.")
        raise SystemExit(1)
    return key