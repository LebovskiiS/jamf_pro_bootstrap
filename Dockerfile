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
RUN wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | apt-key add - \
    && echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | tee -a /etc/apt/sources.list.d/trivy.list \
    && apt-get update \
    && apt-get install -y trivy

# Install code analysis and security tools
RUN pip install --no-cache-dir \
    bandit \
    safety \
    black \
    flake8 \
    pylint \
    mypy \
    pre-commit \
    semgrep \
    pip-audit \
    safety-checker \
    prometheus-client \
    psutil

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

# Copy analyzer configuration files
COPY .bandit ./
COPY .flake8 ./
COPY .pylintrc ./
COPY pyproject.toml ./
COPY .pre-commit-config.yaml ./

# Copy application code
COPY . .

# Create directories for logs, reports and security
RUN mkdir -p /app/logs /app/reports /app/security && \
    chown -R jamf-api:jamf-api /app/logs /app/reports /app/security

# Create security analysis script
RUN echo '#!/bin/bash\n\
    echo "🔒 Container security analysis..."\n\
    \n\
    # Container vulnerability analysis\n\
    echo "🔍 Running Trivy vulnerability scan..."\n\
    trivy image --format json --output /app/reports/trivy-container-report.json . 2>/dev/null || true\n\
    \n\
    # Python dependencies analysis\n\
    echo "🔍 Checking Python dependencies..."\n\
    safety check --json --output /app/reports/safety-report.json 2>/dev/null || true\n\
    pip-audit --format json --output /app/reports/pip-audit-report.json 2>/dev/null || true\n\
    \n\
    # Code security analysis\n\
    echo "🔍 Running code security scan..."\n\
    bandit -r app/ -f json -o /app/reports/bandit-report.json 2>/dev/null || true\n\
    semgrep scan --config=auto --json --output /app/reports/semgrep-report.json app/ 2>/dev/null || true\n\
    \n\
    # Code style and quality analysis\n\
    echo "🎨 Checking code style..."\n\
    black --check app/ --diff > /app/reports/black-report.txt 2>&1 || true\n\
    flake8 app/ --output-file=/app/reports/flake8-report.txt 2>/dev/null || true\n\
    pylint app/ --output=/app/reports/pylint-report.txt 2>/dev/null || true\n\
    mypy app/ --output-file=/app/reports/mypy-report.txt 2>/dev/null || true\n\
    \n\
    # Generate summary report\n\
    echo "📋 Generating summary report..."\n\
    echo "=== SECURITY ANALYSIS REPORT ===" > /app/reports/security-summary.txt\n\
    echo "Date: $(date)" >> /app/reports/security-summary.txt\n\
    echo "Container: $(hostname)" >> /app/reports/security-summary.txt\n\
    echo "" >> /app/reports/security-summary.txt\n\
    \n\
    if [ -f /app/reports/trivy-container-report.json ]; then\n\
    echo "🔴 Container vulnerabilities: $(jq -r ".Vulnerabilities | length" /app/reports/trivy-container-report.json 2>/dev/null || echo "0")" >> /app/reports/security-summary.txt\n\
    fi\n\
    \n\
    if [ -f /app/reports/safety-report.json ]; then\n\
    echo "🔴 Python vulnerabilities: $(jq -r ".vulnerabilities | length" /app/reports/safety-report.json 2>/dev/null || echo "0")" >> /app/reports/security-summary.txt\n\
    fi\n\
    \n\
    if [ -f /app/reports/bandit-report.json ]; then\n\
    echo "🔴 Code security issues: $(jq -r ".results | length" /app/reports/bandit-report.json 2>/dev/null || echo "0")" >> /app/reports/security-summary.txt\n\
    fi\n\
    \n\
    echo "" >> /app/reports/security-summary.txt\n\
    echo "✅ Analysis complete! Results in /app/reports/" >> /app/reports/security-summary.txt\n\
    cat /app/reports/security-summary.txt\n\
    ' > /app/security-scan.sh && chmod +x /app/security-scan.sh

# Switch to user (NOT root!)
USER jamf-api

# Expose only required port
EXPOSE 5000

# Run application with security analysis
CMD ["sh", "-c", "/app/security-scan.sh & python app.py"]
