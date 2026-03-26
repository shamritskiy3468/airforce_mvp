# ✈️ Airspace Simulation & Radar Observation System

## Overview

This project is a high‑fidelity simulation of airspace activity within any selected geographic area. Its primary purpose is to emulate the behavior of real‑world radar‑based airspace surveillance systems and provide a continuous, realistic stream of detection events.

The system models both the **“truth layer”** (actual aircraft positions and movements) and the **“radar layer”** (imperfect observations produced by multiple independent radar stations). The result is a dynamic environment suitable for testing tracking algorithms, fusion logic, and real‑time airspace monitoring workflows.

---

## 🎯 Project Goals

The simulation aims to reproduce the essential characteristics of real radar‑based airspace monitoring:

- Continuous 24/7 scanning of the airspace  
- Multiple radar stations operating simultaneously  
- Realistic imperfections and inconsistencies in observations  
- Real‑time event streaming and processing  
- End‑to‑end pipeline from raw radar hits to fused air picture  

---

## 🛰️ Radar Layer (Observation Simulation)

Each of the **N radar stations** performs a continuous 360° scan of the airspace. For every detected aircraft, a radar produces:

- Range (distance / coordinates)  
- Altitude  
- Velocity (computed as Δposition over time T)

To mimic real‑world limitations, the radar layer introduces:

- Duplicate detections of the same aircraft from different stations  
- Temporary loss of track (terrain masking, curvature of Earth, clutter, weather, etc.)  
- Noise, gaps, and inconsistencies in measurements  
- Varying detection probability depending on geometry and environment  

This creates a realistic, imperfect observation environment — just like real air traffic surveillance systems.

---

## ✈️ Aircraft Simulation (“Source of Truth”)

The aircraft world operates as a perfect, noise‑free model of reality. Each aircraft has:

- True position  
- True velocity  
- True altitude  
- Deterministic or scripted movement patterns  

The radar layer observes this world and produces noisy, incomplete data streams.

---

## 🧠 Processing & Fusion Objectives

The system is designed to support and test advanced air‑tracking algorithms, including:

- **Interpolation** — filling gaps between radar hits  
- **Smoothing** — reducing noise and jitter in measurements  
- **Prediction** — estimating future aircraft positions  
- **(Near) real‑time tracking** — maintaining stable tracks over time  
- **Deduplication** — merging multiple radar detections into a single coherent track  

These components together form a complete airspace picture generation pipeline.

---

## 📡 End‑to‑End Flow

- Truth Model (Aircraft World + Physics)
                    ↓
- Radar Simulation Layer (Noise, gaps, duplicates)
                    ↓
- Event Stream (continuous radar hits)
                    ↓
- Processing Pipeline (fusion, tracking, prediction)
                    ↓
- Airspace Picture (clean, deduplicated, real‑time)


---

## 🚀 Purpose of the Project

This project serves as a sandbox for experimenting with:

- Multi‑sensor fusion  
- Real‑time tracking algorithms  
- Radar data processing  
- Airspace visualization  
- System robustness under imperfect data  

It is ideal for research, prototyping, and educational exploration of air surveillance systems.
