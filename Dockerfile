FROM python:3.11-slim

# Install required system packages
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Cursor CLI
RUN curl https://cursor.com/install -fsS | bash || (echo "Cursor CLI installation failed" && exit 1)

# Add ~/.local/bin to PATH (where Cursor CLI is installed)
ENV PATH="/root/.local/bin:${PATH}"

# Verify Cursor CLI installation
RUN agent --version || (echo "Cursor CLI verification failed" && exit 1)

# Set working directory
WORKDIR /workspace

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install package so orchestragent and config are importable without sys.path
RUN pip install --no-cache-dir -e .

# Allow all operations for Cursor CLI (inside container)
ENV CURSOR_CONFIG_DIR="/root/.orchestragent"
RUN mkdir -p /root/.orchestragent
COPY cli-config.template.json /root/.orchestragent/cli-config.json

# Make scripts executable
RUN chmod +x scripts/setup.sh || true && \
    chmod +x scripts/entrypoint.sh || true

# Entrypoint: scripts/entrypoint.sh runs git user config, initial setup, and dashboard startup
CMD ["scripts/entrypoint.sh"]
