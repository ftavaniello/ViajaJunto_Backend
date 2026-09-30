FROM python:3.13-slim

# 1. Atualiza os pacotes do sistema operacional para corrigir as vulnerabilidades do Debian/OpenSSL
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

# 2. Define o diretório de trabalho
WORKDIR /app


# 3. Atualiza o pip e setuptools para versões seguras antes de instalar as dependências
RUN pip install --no-cache-dir --upgrade pip setuptools msgpack urllib3

# Em seguida, instala o restante das dependências do projeto
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copia o restante do código da aplicação
COPY . .

# 5. Comando de inicialização
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]