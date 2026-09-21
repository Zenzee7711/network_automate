# Network Automation

## Overview

This project demonstrates a simple network automation system for executing Cisco router commands through a web-based interface.

The system uses a FastAPI backend, an Nginx frontend, Docker Compose, and SSH connectivity to Cisco routers.

## Architecture

The project consists of two Docker containers:

- **Frontend** — HTML/CSS/JavaScript web interface served by Nginx
- **Backend** — FastAPI application that connects to Cisco routers using Paramiko
- **Cisco Routers** — R1 and R2 accessed through SSH

```text
Web Browser
     |
     | HTTP :8080
     v
Frontend (Nginx)
     |
     | /api/
     v
Backend (FastAPI :8000)
     |
     | SSH :22
     +-------------> Cisco R1
     |
     +-------------> Cisco R2
