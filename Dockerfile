# Start with a slim Debian base
FROM debian:bullseye-slim as builder

# Install dependencies
RUN apt-get update && apt-get install -y \
    wget \
    build-essential \
    libssl-dev \
    zlib1g-dev \
    libncurses5-dev \
    libncursesw5-dev \
    libreadline-dev \
    libsqlite3-dev \
    libgdbm-dev \
    libdb5.3-dev \
    libbz2-dev \
    libexpat1-dev \
    liblzma-dev \
    tk-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Download and install Python 3.12.3
RUN wget https://www.python.org/ftp/python/3.12.3/Python-3.12.3.tgz \
    && tar xzf Python-3.12.3.tgz \
    && cd Python-3.12.3 \
    && ./configure --enable-optimizations \
    && make altinstall \
    && cd .. \
    && rm -rf Python-3.12.3 Python-3.12.3.tgz

# Start a new stage for the final image
FROM debian:bullseye-slim as app

# Copy Python from builder stage
COPY --from=builder /usr/local /usr/local

# Set up the working directory
WORKDIR /usr/src/app

# Copy requirements file
COPY requirements.txt ./

# Install pip and the required packages
RUN apt-get update && apt-get install -y \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/* \
    && python3.12 -m ensurepip \
    && python3.12 -m pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application
COPY . ./
COPY images/ ./images

# Set environment variables
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8


# Set the command to run your application
CMD ["python3.12", "sql_generate.py"]

EXPOSE 7860