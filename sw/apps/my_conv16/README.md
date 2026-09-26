# 💻 Software Stack & Bare-Metal Driver (`sw`)

## 📋 Table of Contents
1. [Overview](#overview)
2. [File Structure](#file-structure)
3. [Core Implementation](#core-implementation)
4. [External Validations (Sim & MNIST)](#external-validations)
5. [Software-Hardware Execution Flow](#execution-flow)

---

<a id="overview"></a>
## 📌 Overview

The `sw` directory contains the host-side software stack responsible for configuring, feeding, and managing the FPGA hardware accelerator. This includes the Bare-Metal C application that runs on the embedded host processor, alongside Python utility scripts used for generating test vectors and parsing outputs.

---

<a id="file-structure"></a>
## 📂 File Structure

This directory houses the core application and data generation utilities for the `my_conv16` accelerator:

| File | Type | Purpose |
| :--- | :--- | :--- |
| **`my_conv16.c`** | Core Code | Bare-Metal C driver managing the hardware accelerator via Control & Status Registers (CSRs). |
| **`gen_conv_test.py`** | Test Generator | Python script that creates randomized input matrices and hardware configurations. |
| **`process_conv_results.py`** | Utility | Python script to parse and format the hardware's output feature maps. |

---

<a id="core-implementation"></a>
## 📄 Core Implementation (`my_conv16.c`)

The primary C application acts as the master controller for the 2D Convolution RTL hardware.

**Key Operations:**
- **Memory Mapping:** Loads input images and kernel weights into the designated shared DRAM addresses.
- **Hardware Configuration:** Configures the hardware Control & Status Registers (CSRs) with dynamic architectural parameters.
- **Execution & Polling:** Asserts the `START` signal to trigger the accelerator and continuously polls the `DONE` interrupt flag to detect completion.
- **Data Retrieval:** Extracts the processed 16x16 output feature map from DRAM once the hardware signals completion.

**Compile-Time Flags:**
- `-ccd1 XON`: Enables the hardware acceleration execution mode.

---

<a id="external-validations"></a>
## 🔗 External Validations (Simulation & MNIST)

The software stack works in tandem with external environments to verify the algorithmic and hardware correctness:

*   **Cycle-Accurate Simulation (`sim`):** For automated error checking (MSE), the Python Golden Reference model, and detailed simulation logs, refer to the [Simulation Environment README](../sim/README.md).
*   **MNIST Validation (`MNIST_py`):** To evaluate the hardware architecture against real-world datasets, the project utilizes the `MNIST_py` environment. This directory contains the specific validation script (`MNIST_and_our_conv.py`), the image dataset (`MNISTdata.hdf5`), and the C++ pipeline library (`pipeline.dll`). For more details, refer to the [MNIST_py README](../MNIST_py/README.md).

---

<a id="execution-flow"></a>
## 🔄 Software-Hardware Execution Flow

The following diagram illustrates the execution sequence managed by the software stack, demonstrating how it bridges the gap between test generation and hardware execution:

```mermaid
flowchart TD
    subgraph SW_Environment [Software Setup: sw/apps/my_conv16]
        GEN[gen_conv_test.py\nGenerate Vectors]
        APP[my_conv16.c\nBare-Metal App]
        PROC[process_conv_results.py\nParse Results]
    end

    subgraph Shared_Memory [System DRAM / File I/O]
        direction TB
        CONFIG[(Input Vectors:\nconv_input.txt\nconv_kernels.txt)]
        HW_OUT[(Raw Output:\nconv_output.txt)]
    end

    subgraph HW_Accelerator [FPGA RTL]
        FSM[Hardware Execution]
    end

    GEN -->|Writes| CONFIG
    CONFIG -->|Reads| APP
    APP -->|Configures & Triggers| FSM
    FSM -->|Writes| HW_OUT
    HW_OUT -->|Reads| APP
    APP -->|Passes Data| PROC
