FROM python:3.13-slim

# 1. Atualiza os pacotes do sistema operacional para corrigir as vulnerabilidades do Debian/OpenSSL
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

# 2. Define o diretório de trabalho
WORKDIR /app

# 3. Copia os arquivos de dependências e instala as versões atualizadas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copia o restante do código da aplicação
COPY . .

# 5. Comando de inicialização
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]