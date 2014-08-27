#!/bin/bash

# Install Redis
apt-get update
apt-get install -y redis-server

# Show versions
dpkg -la | grep redis-server