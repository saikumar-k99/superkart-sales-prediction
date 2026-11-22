FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Install the dependencies first (without cache, to keep the image small) so that this layer is reused
# when only the application code or the model changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code and the serialized model to the container's working directory
COPY . .

# The API listens on port 7860
EXPOSE 7860

# Define the command to start the application using Gunicorn with 4 worker processes
# - `-w 4`: Uses 4 worker processes for handling requests
# - `-b 0.0.0.0:7860`: Binds the server to port 7860 on all network interfaces
# - `app:superkart_api`: Runs the Flask app (assuming `app.py` contains the Flask instance named `superkart_api`)
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:7860", "app:superkart_api"]
