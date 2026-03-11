import subprocess
import sys


def install_requirements():
    requirements = ["streamlit", "streamlit-option-menu"]

    for package in requirements:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            print(f"Установка {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])


if __name__ == "__main__":
    install_requirements()

    subprocess.run(["streamlit", "run", "main_app.py"])