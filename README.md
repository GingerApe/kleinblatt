# Project Setup and Quick Start Guide

Welcome to the project! This guide will help you set up the environment and run the application smoothly on both Windows and macOS.

## Prerequisites

Before you begin, ensure you have met the following requirements:

- **Python 3.8 or later**: The application requires Python 3.8 or later. You can download it from the [official Python website](https://www.python.org/downloads/).

## Installation

### Step 1: Install Python

#### Windows

1. Download the Python installer from the [Python website](https://www.python.org/downloads/windows/).
2. Run the installer and ensure you check the box that says "Add Python to PATH".
3. Follow the installation steps.

#### macOS

1. Download the Python installer from the [Python website](https://www.python.org/downloads/macos/).
2. Run the installer and follow the installation steps.

### Step 2: Set Up a Virtual Environment

A virtual environment helps manage dependencies and avoid conflicts. Follow these steps to create one:

1. Open a terminal (Command Prompt on Windows, Terminal on macOS).
2. Navigate to the project directory:
   ```bash
   cd path/to/your/project
   ```
3. Create a virtual environment:
   ```bash
   python -m venv venv
   ```
4. Activate the virtual environment:

   - **Windows**:
     ```bash
     venv\Scripts\activate
     ```
   - **macOS**:
     ```bash
     source venv/bin/activate
     ```

### Step 3: Install Dependencies

With the virtual environment activated, install the required packages using pip:

bash
pip install -r requirements.txt


### Step 4: Run the Application

Once the dependencies are installed, you can run the application:

1. Ensure your virtual environment is activated.
2. Execute the main script:

   - **Windows**:
     ```bash
     python main.py
     ```
   - **macOS**:
     ```bash
     python3 main.py
     ```

## Additional Information

- **Deactivating the Virtual Environment**: When you're done, you can deactivate the virtual environment by simply typing `deactivate` in the terminal.
- **Reactivating the Virtual Environment**: If you close the terminal, you'll need to reactivate the virtual environment before running the application again.

## Troubleshooting

- If you encounter any issues, ensure that Python is correctly installed and added to your system's PATH.
- Verify that the virtual environment is activated before installing dependencies or running the application.

Thank you for using our application! If you have any questions or need further assistance, feel free to reach out.