import os
from pathlib import Path


CUR_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CUR_DIR.parent
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

if __name__ == '__main__':
    print(DATA_DIR)

