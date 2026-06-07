FROM python:3.11-slim

# 1. Installer les dépendances système
RUN apt-get update && apt-get install -y \
    git \
    git-lfs \
    ffmpeg \
    libsm6 \
    libxext6 \
    cmake \
    rsync \
    libgl1 \
    && rm -rf /var/lib/apt/lists/* \
    && git lfs install

# 2. Créer l'utilisateur standard imposé par Hugging Face
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

# ---> LA SOLUTION EST ICI : Créer le fichier pour faire taire Streamlit <---
RUN mkdir -p /home/user/.streamlit \
    && echo "[general]\nemail = \"\"\n" > /home/user/.streamlit/credentials.toml

WORKDIR /app

# 3. Copier les fichiers en donnant la propriété à 'user'
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=user:user . .

# 4. Lancer l'application en mode headless forcé
EXPOSE 7860
CMD ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0", "--server.headless=true"]
