# Use a minimal base image with Python 3.11 installed
FROM python:3.11-slim

# Set the working directory inside the container to /app
WORKDIR /app

# Install Python dependencies listed in requirements.txt (this layer is reused when only the code changes)
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the application code from the host to the container's /app directory
COPY . .

# The UI listens on port 8501
EXPOSE 8501

# Define the command to run the Streamlit app on port 8501 and make it accessible externally
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true", "--server.enableXsrfProtection=false"]
