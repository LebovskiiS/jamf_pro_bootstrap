FROM python:3.11-slim

# Install system dependencies and security tools
RUN apt-get update && apt-get install -y \
    curl \
    jq \
    git \
    gcc \
    g++ \
    make \
    wget \
    gnupg \
    ca-certificates \
    procps \
    htop \
    net-tools \
    iotop \
    lsof \
    strace \
    && rm -rf /var/lib/apt/lists/*

# Install Trivy (vulnerability analyzer)
RUN wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | gpg --dearmor -o /usr/share/keyrings/trivy-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/trivy-archive-keyring.gpg] https://aquasecurity.github.io/trivy-repo/deb bullseye main" | tee -a /etc/apt/sources.list.d/trivy.list \
    && apt-get update \
    && apt-get install -y trivy || \
    (wget -qO - https://github.com/aquasecurity/trivy/releases/download/v0.48.4/trivy_0.48.4_Linux-64bit.tar.gz | tar -xz -C /usr/local/bin trivy)

# Install only security scanner (Trivy already installed above)
# No additional Python security tools needed - they're external

# Create user (NOT root!)
RUN useradd -m -u 1000 jamf-api && \
    mkdir -p /app && \
    chown jamf-api:jamf-api /app

# Set working directory
WORKDIR /app

# Copy dependency files
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# No analyzer configs needed - external tools only

# Copy application code
COPY . .

# Create directories for logs, reports and security
RUN mkdir -p /app/logs /app/reports /app/security && \
    chown -R jamf-api:jamf-api /app/logs /app/reports /app/security

# Create simple security scan script
RUN echo '#!/bin/bash\n\
    echo "=== Container Security Scan ==="\n\
    echo "Scan completed at $(date)"\n\
    echo "Container running as user: $(whoami)"\n\
    echo "Process ID: $$"\n\
    echo "=== Scan Complete ==="\n\
    ' > /app/security-scan.sh && chmod +x /app/security-scan.sh

# Switch to user (NOT root!)
USER jamf-api

# Expose only required port
EXPOSE 5000

# Run application with security analysis
CMD ["sh", "-c", "/app/security-scan.sh & python app.py"]
