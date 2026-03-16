# Ak Maintenance X

A Python developer tool for securely inspecting and managing X (Twitter) account activity using the X API.

This project authenticates using OAuth 2.0 Authorization Code Flow with PKCE and allows safe automation of account maintenance tasks such as inspecting likes, reposts, follows, and posts.

## Features

- OAuth2 authentication with PKCE
- Secure API access using access tokens
- Local callback server for authentication
- Environment-based secret management
- Modular Python architecture

Future features include:

- Inspect liked tweets
- Bulk unlike tweets
- Inspect reposts
- Remove reposts
- Inspect following list
- Bulk unfollow accounts
- Inspect user tweets
- Delete tweets safely

## Project Structure

ak-maintenance-x
│
├── auth_test.py
├── requirements.txt
├── .env.example
├── README.md
└── docs/

## Setup

### 1 Install dependencies

pip install -r requirements.txt

### 2 Create environment file

cp .env.example .env

Add your X API credentials.

### 3 Run authentication test

python auth_test.py

## Technologies Used

- Python
- X API v2
- OAuth 2.0 Authorization Code Flow
- PKCE Authentication
- Requests library

## Author

Akinola Ogunbiyi  
Former Division-I athlete transitioning into software engineering and DevOps.