# SunCast backend container for Hugging Face Spaces (Docker SDK)
FROM python:3.11-slim

# Hugging Face runs the container as a normal user, not root
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"
WORKDIR /home/user/app

# Install the libraries first so rebuilds are faster
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend code (and data/retailers.csv)
COPY --chown=user . .

# Hugging Face Spaces expects the app on port 7860
EXPOSE 7860
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
