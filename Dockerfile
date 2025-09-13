FROM python:3.12-slim

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install uv and dependencies
RUN pip install uv && uv sync --frozen --no-install-project --no-dev

# Copy source code
COPY . .

# Run the bot
CMD ["uv", "run", "python", "main.py"]
