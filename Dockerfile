# Use the official Python image as the base image
FROM python:3.11-slim

# Set environment variables
# FIX: Changed ENV format from 'key value' to 'key=value' to resolve build warnings.
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_PORT=8501
EXPOSE 8501

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Streamlit application file
COPY app.py .
COPY om_extract.py .
COPY siteList.csv .
COPY getNearby.py .
COPY obsData.py .


# Command to run the application
# Streamlit must be run using 'streamlit run'
CMD ["streamlit", "run", "app.py"]