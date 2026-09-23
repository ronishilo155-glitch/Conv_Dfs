# ⚙️ FPGA-Based CNN Hardware Accelerator for 2D Convolution

## 📌 Project Overview

This project implements a dedicated custom hardware accelerator for two-dimensional (2D) convolution, designed to accelerate Convolutional Neural Networks (CNNs) on an FPGA platform.

The primary motivation is to overcome the **"Memory Wall"** bottleneck. In standard processors, overlapping sliding windows in convolution require repeatedly fetching the same pixels from external DRAM, causing severe performance degradation. This architecture resolves the bottleneck by implementing a **Tile-Based Fused Pipeline** with on-chip dual buffering, which maximizes data reuse and minimizes external memory latency.

---

## 🧠 Algorithmic Acceleration Model (Non-Overlapping LWCNN)

The accelerator adopts the fully-fused layer principles from LightWeight CNN (LWCNN) architectures. By enforcing non-overlapping convolution windows (2x2 kernel with stride 2), the spatial dimension reduces by a factor of 4 at each consecutive layer.

```mermaid
flowchart TD
    subgraph Input_Image [Input Grayscale Image: 256x256]
        T1[16x16 Receptive Field / Tile]
    end

    subgraph Layer1 [Layer 1: Conv1 + Pool1]
        RF1[8x8 Receptive Field]
    end

    subgraph Layer2 [Layer 2: Conv2 + Pool2]
        RF2[4x4 Receptive Field]
    end

    subgraph Downstream [Subsequent Reductions]
        RF3[2x2 Receptive Field]
        ACT[1x1 Single Activation]
    end

    subgraph Classifier [Classification Layer]
        FC[Fully-Connected: 256 Inputs]
        OUT[Binary Output Classes]
    end

    T1 -->|2x2 Conv Stride 2| RF1
    RF1 -->|2x2 Conv Stride 2| RF2
    RF2 -->|2x2 Conv Stride 2| RF3
    RF3 -->|2x2 Conv Stride 2| ACT
    ACT -->|Streamed Accumulation| FC
    FC --> OUT
