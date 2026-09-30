# SmartPark — FYP Monorepo

👉👉👉 **GitHub Repository:** [https://github.com/gx040502/smartpark-fyp-monorepo](https://github.com/gx040502/smartpark-fyp-monorepo) 👈👈👈

An AI-powered smart parking management system built as a Final Year Project (FYP). The system handles license plate recognition (LPR), traffic congestion detection, an AI-powered natural-language query agent, and full-stack web + mobile interfaces.

> For training datasets, model outputs, and test results, see [DATASETS.md](DATASETS.md).

---

## Table of Contents

- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup Guide](#setup-guide)
  - [1. Clone the Repository](#1-clone-the-repository)
  - [2. Download YOLO Model Weights](#2-download-yolo-model-weights)
  - [3. Database Setup (MySQL)](#3-database-setup-mysql)
  - [4. Backend (Laravel)](#4-backend-laravel)
  - [5. Frontend (Next.js)](#5-frontend-nextjs)
  - [6. Mobile App (React Native / Expo)](#6-mobile-app-react-native--expo)
  - [7. Python Services (Conda)](#7-python-services-conda)
    - [AI Service](#ai-service)
    - [LPR (License Plate Recognition)](#lpr-license-plate-recognition)
    - [Traffic Congestion](#traffic-congestion)
- [Running the Project](#running-the-project)
- [Environment Variables](#environment-variables)

---

## Project Structure

```
FYP DEVELOPMENT/
├── backend/                  # Laravel 13 REST API (PHP 8.3+)
├── frontend/                 # Next.js 16 admin dashboard
├── mobile-frontend/          # React Native (Expo) mobile app
├── ai-service/               # FastAPI — AI agent (Text-to-SQL via HuggingFace / Ollama)
├── LPR/                      # License Plate Recognition pipeline (YOLO + OpenCV)
│   └── yolov8n.pt            # Pre-trained YOLOv8n (car detection fallback)
├── traffic-congestion/       # Traffic congestion detection (YOLO + ByteTrack)
├── tests/                    # Postman / integration tests
├── cars.pt                   # YOLO model — car detection (not in repo, see DATASETS.md)
├── plate.pt                  # YOLO model — license plate detection
├── OCR.pt                    # YOLO model — character recognition
├── car make.pt               # YOLO model — brand/make classification
├── environment.yml           # Conda environment for all Python services
├── DATASETS.md               # Google Drive links to datasets & outputs
└── .gitignore
```

---

## Prerequisites

Make sure you have the following installed before proceeding:

| Tool | Version | Used By |
|---|---|---|
| **Anaconda / Miniconda** | Latest | ai-service, LPR, traffic-congestion |
| **Node.js** | v24+ | frontend, mobile-frontend |
| **npm** | v11+ | frontend, mobile-frontend |
| **PHP** | 8.3+ | backend |
| **Composer** | 2.x | backend |
| **MySQL** | 8.x | backend, ai-service |
| **Expo CLI** | Latest | mobile-frontend |
| **YOLO Model Weights** | — | LPR, traffic-congestion (see below) |

> **Note:** YOLO `.pt` weight files are **not included** in the repository (they are gitignored due to their large size). Download them from the shared Google Drive folder documented in [DATASETS.md](DATASETS.md) and place them in the project root directory (`cars.pt`, `plate.pt`, `OCR.pt`, `car make.pt`).

---

## Setup Guide

### 1. Clone the Repository

```bash
git clone https://github.com/gx040502/smartpark-fyp-monorepo.git
cd smartpark-fyp-monorepo
```

---

### 2. Download YOLO Model Weights

The YOLO `.pt` model files are **not included** in the repository due to their large size. Download them from the shared [Google Drive folder](https://drive.google.com/drive/folders/1DjFkW60xzg6ffigRr-FVnq4-lPlhupTo?usp=sharing) and place them in the **project root directory**.

| File to create | Download from (Google Drive path) |
|---|---|
| `cars.pt` | `CAR MODEL/outputs/car_mixed/yolo11_run_01/weights/best.pt` |
| `plate.pt` | `LICENSE PLATE/outputs/License-Plate-Recognition-11/yolo11_run_02/weights/best.pt` |
| `OCR.pt` | `OCR/outputs/CatEye-ALPR-v3-3/yolo8_run_01/weights/best.pt` |
| `car make.pt` | `CAR_CLASSIFICATION/outputs/version4_split/yolo_cls_run_01/weights/best.pt` |

After downloading, your project root should look like:

```
smartpark-fyp-monorepo/
├── cars.pt
├── plate.pt
├── OCR.pt
├── car make.pt
├── backend/
├── frontend/
├── ...
```

> For full details on all available datasets and outputs, see [DATASETS.md](DATASETS.md).

---

### 3. Database Setup (MySQL)

1. Create a MySQL database:

```sql
CREATE DATABASE fyp_parking;
```

2. The database tables will be created automatically when you run the Laravel migrations (see step 4).

---

### 4. Backend (Laravel)

```bash
cd backend

# Install PHP dependencies
composer install

# Copy environment file and configure it
cp .env.example .env

# Generate application key
php artisan key:generate
```

Then edit `backend/.env` to set your database credentials:

```
DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=fyp_parking
DB_USERNAME=root
DB_PASSWORD=
```

Run the database migrations:

```bash
php artisan migrate
```

Start the backend server:

```bash
php artisan serve
# Runs on http://127.0.0.1:8000
```

---

### 5. Frontend (Next.js)

```bash
cd frontend

# Install Node.js dependencies
npm install

# Start development server
npm run dev
# Runs on http://localhost:3000
```

> **Optional:** Create a `.env.local` file in `frontend/` to override the API URL:
> ```
> NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api
> ```

---

### 6. Mobile App (React Native / Expo)

```bash
cd mobile-frontend

# Install Node.js dependencies
npm install

# Start Expo development server
npx expo start
```

> **Note:** If running on a physical device, update the API base URL in  
> `mobile-frontend/src/api/client.ts` to your machine's local IP address (e.g., `http://192.168.1.100:8000/api`).

---

### 7. Python Services (Conda)

All three Python services (`ai-service`, `LPR`, `traffic-congestion`) share the same Conda environment.

#### Create the Conda environment

```bash
# From the project root directory
conda env create -f environment.yml
conda activate plate_recognition
```

> The environment uses **Python 3.11** and includes PyTorch with CUDA 12.9 support, Ultralytics (YOLO), OpenCV, FastAPI, and more.

#### Each service also has its own `requirements.txt` if you prefer pip:

```bash
pip install -r ai-service/requirements.txt
pip install -r LPR/requirements.txt
pip install -r traffic-congestion/requirements.txt
```

---

#### AI Service

Text-to-SQL AI agent powered by HuggingFace Inference API or local Ollama.

```bash
cd ai-service

# Copy and configure environment variables
cp .env.example .env
# Edit .env — set your HUGGINGFACE_API_TOKEN and database credentials

# Start the service
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
# Runs on http://localhost:8001
```

**Required `.env` variables:**
| Variable | Description |
|---|---|
| `HUGGINGFACE_API_TOKEN` | Your HuggingFace API token |
| `PROVIDER` | `huggingface` or `ollama` |
| `LARAVEL_API_URL` | Laravel backend URL (default: `http://127.0.0.1:8000/api`) |
| `MODEL_ID` | HuggingFace model ID |
| `DB_HOST`, `DB_PORT`, `DB_USERNAME`, `DB_PASSWORD`, `DB_DATABASE` | MySQL connection |

---

#### LPR (License Plate Recognition)

YOLO-based license plate detection, OCR, and car attribute extraction.

```bash
cd LPR

# Copy and configure environment variables
cp .env.example .env
# Edit .env — set your HF_TOKEN

# Run entrance gate LPR
python LPR_enter_no_qwen.py

# Run exit gate LPR
python LPR_exit_no_qwen.py
```

**Required `.env` variables:**
| Variable | Description |
|---|---|
| `HF_TOKEN` | Your HuggingFace API token |
| `LARAVEL_API_URL` | Laravel backend URL (default: `http://127.0.0.1:8000`) |

> **Important:** Update the YOLO model paths at the top of each script (`PLATE_MODEL_PATH`, `OCR_MODEL_PATH`, `BRAND_MODEL_PATH`) to point to your trained `.pt` weight files.

---

#### Traffic Congestion

YOLO + ByteTrack vehicle tracking for real-time traffic congestion detection.

```bash
cd traffic-congestion

# Start the service
uvicorn main:app --host 0.0.0.0 --port 8002 --reload
# Runs on http://localhost:8002
```

> **Important:** Update `YOLO_MODEL_PATH` at the top of `main.py` to point to your car detection model weights.

---

## Running the Project

To run the full system, start the services in this order:

| # | Service | Command | Port |
|---|---|---|---|
| 1 | **MySQL** | Start your MySQL server | `3306` |
| 2 | **Backend** | `cd backend && php artisan serve` | `8000` |
| 3 | **Frontend** | `cd frontend && npm run dev` | `3000` |
| 4 | **AI Service** | `cd ai-service && uvicorn main:app --port 8001 --reload` | `8001` |
| 5 | **Traffic Congestion** | `cd traffic-congestion && uvicorn main:app --port 8002 --reload` | `8002` |
| 6 | **Mobile App** | `cd mobile-frontend && npx expo start` | `8081` |
| 7 | **LPR** | `cd LPR && python LPR_enter_no_qwen.py` | — |

---

## Environment Variables

Every service that requires secrets uses a `.env` file (gitignored). Template `.env.example` files are provided:

| Service | Template File |
|---|---|
| `backend/` | `backend/.env.example` |
| `ai-service/` | `ai-service/.env.example` |
| `LPR/` | `LPR/.env.example` |

Copy each `.env.example` to `.env` and fill in your values before running.

```bash
cp backend/.env.example backend/.env
cp ai-service/.env.example ai-service/.env
cp LPR/.env.example LPR/.env
```
