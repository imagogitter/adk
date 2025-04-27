# InfluxDB Setup Guide

This document outlines the steps needed to initialize and configure InfluxDB for the autonomous trading platform.

## Prerequisites

- Docker and Docker Compose installed
- Access to the project's `.env` file

## Initial Setup Steps

### 1. Start the InfluxDB Container

```bash
cd docker
docker-compose up -d influxdb
