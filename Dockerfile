FROM python:3.13-slim

# 1. Atualiza os pacotes do sistema operacional para corrigir as vulnerabilidades do Debian/OpenSSL
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

# 2. Define o diretório de trabalho
WORKDIR /app

# 3. Atualiza o pip para a versão mais recente
RUN pip install --no-cache-dir --upgrade pip

# 4. Copia os requisitos e força o upgrade completo de todas as dependências listadas
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# 5. Copia o restante do código da aplicação
COPY . .

# 6. Comando de inicialização
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]