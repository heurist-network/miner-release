# Heurist Miner

For GPU Ninjas: You can skip any of these steps if you already have the toolkits installed. 

- If you have installed Python 3.x, you possibly don't need to install Miniconda and latest Python again if you can handle the dependency installation in Step 5 and 7, but it's recommended that you still go through Step 2 and 3 to manage Python dependencies with Conda environment. 
- If you have installed CUDA before, you need to install the matching PyTorch version in Step 5 to work with your CUDA version.

**This is a preview version of testnet mining program. You may meet some unexpected problems when setting it up. Heurist team can help answer your questions in [Discord #miner-chat channel]( https://discord.gg/bmdfAgufFa)**

## Windows Setup Guide

### Step 1. (Optional) Update GPU drivers

1. Go to the [NVIDIA Driver Downloads](https://www.nvidia.com/Download/index.aspx) page.

2. Select your GPU model and OS.

3. Download and install the latest driver. Restart your PC if necessary.

### Step 2. Install Miniconda

1. Download the Miniconda Installer. 
- Visit the [Miniconda Downloads page](https://docs.conda.io/projects/miniconda/en/latest/). 
- Get the latest Windows 64-bit version for Python 3.11.
conda activate pytorch-gpu-python-3-10.
### Step 3. Create a Conda Environment

1. Open a command prompt (Win + X > “Command Prompt”).

2. Create the Environment:
- Type `conda create --name gpu-3-11 python=3.11` (or choose your Python version).
- Press Enter and wait for the process to finish.

3. Activate the Environment
- Type `conda activate gpu-3-11`

### Step 4: Install CUDA Toolkit
1. Download and Install CUDA:
- Visit the [CUDA Toolkit 12.1 download page](https://developer.nvidia.com/cuda-12-1-0-download-archive?target_os=Windows&target_arch=x86_64&target_version=11&target_type=exe_local).
- Select your OS version.
- Download and install it by following the prompts.

### Step 5: Install PyTorch with GPU Support
1. Go to the [PyTorch Install Page](https://pytorch.org/get-started/locally/).
- Set Your Preferences: Choose PyTorch, Conda, CUDA 12.1
- Install PyTorch: Copy the generated command (like `conda install pytorch torchvision torchaudio pytorch-cuda=12.1 -c pytorch -c nvidia`). Paste it in the Command Prompt and hit Enter.

### Step 6: Download Miner Scripts
1. Run `git clone https://github.com/heurist-network/miner-release` in command prompt. Or Click "Code -> Download ZIP" in this [Github repo - miner-release](https://github.com/heurist-network/miner-release) to download miner scripts.

### Step 7: Install Dependencies from `requirements.txt`

1. Open Your Command Prompt
- Make sure you're still in your Conda environment. If not, activate it again with `conda activate gpu-3-11`

2. Navigate to `miner-release` folder
- Use the cd command to change directories to where `requirements.txt` is located. For example, `cd C:\Users\YourUsername\Documents\miner-release`.

3. Install Dependencies:
- `Run the command pip install -r requirements.txt`. This command tells pip (Python's package installer) to install all the packages listed in your requirements.txt file.

### Step 8. Configuring Your Miner ID with a .env File
1. **Create a `.env` File:** Navigate to the root directory of your `miner-release` folder. Here, create a new file named `.env`. This file will hold the unique identifiers (miner IDs) for your mining operation.
2. **Define Unique Miner IDs:** In the `.env` file, you will assign a unique Ethereum wallet address as a miner ID for each of your GPUs. These Ethereum addresses will serve as the miner IDs, which are crucial for tracking your contributions and ensuring you receive rewards accurately.

    Use the following format to define each miner ID in the `.env` file, ensuring that each Ethereum address starts with `0x` and is unique to each GPU:

    ```plaintext
    MINER_ID_0=0xYourFirstWalletAddressHere
    MINER_ID_1=0xYourSecondWalletAddressHere
    ```

    Continue this pattern for as many GPUs as you have, assigning a unique wallet address to each one. For instance, if you have three GPUs, you would define `MINER_ID_0`, `MINER_ID_1`, and `MINER_ID_2`, each with a different Ethereum wallet address.

3. **Configure Multiple GPUs:** If your mining setup includes multiple GPUs, ensure that you've created a line in the `.env` file for each one, following the pattern described above. If you use the same miner_id for multiple GPUs, the protocol will recognize you as one GPU. Make sure you set unique miner_id for each GPU to receive rewards correctly.

### Step 9. Run the miner program
1. Run `python3 sd-miner-v0.0.x.py` (select the latest version of file) in Conda environment command prompt.

2. Type `yes` when the program prompts you to download model files. It will take a while to download all models. The program will start processing automatically once it completes downloading.

### Step 10. (Optional) Enhancing Your Mining Experience with CLI Options
To optimize and customize your mining operations, you can utilize the following command line interface (CLI) options when starting the miner:

#### `--log-level`
Control the verbosity of the miner's log messages by setting the log level. Available options are `DEBUG`, `INFO` (default), `WARNING`, `ERROR`, and `CRITICAL`.
#### `--auto-confirm`
Automate the download confirmation process, especially useful in automated setups. Use `yes` to auto-confirm or stick with `no` (default) for manual confirmation.

**Usage Example:**
```bash
python sd-miner.py --log-level DEBUG --auto-confirm yes
```
Congratulations! 🌟 You're now set to serve image generation requests. You don't need to keep it up 24/7. Feel free to close the program whenever you need your GPU like playing video games or streaming videos.

## Linux Setup Guide
This guide assumes you're familiar with the terminal and basic Linux commands. Most steps are similar to the Windows setup, with adjustments for Linux-specific commands and environments.

- Python Installation: If Python 3.x is already installed, you can skip the Miniconda installation. However, using Miniconda or Conda to manage dependencies is still recommended.
- CUDA: If CUDA is previously installed, ensure the PyTorch installation matches your CUDA version.

### Step 1. Update GPU drivers (Optional)
- Use your Linux distribution's package manager or download drivers directly from the NVIDIA website. For Ubuntu, you might use commands like `sudo apt update` and `sudo ubuntu-drivers autoinstall`.

### Step 2. Install Miniconda or Conda (Optional)
- Download the Miniconda installer for Linux from the [Miniconda Downloads page](https://docs.anaconda.com/free/miniconda/).
- Use the command line to run the installer.
  
### Step 3. Create a Conda Environment
- Open a terminal.
- Create a new environment with `conda create --name gpu-3-11 python=3.11`.
- Activate the environment using `conda activate gpu-3-11`.

### Step 4: Install CUDA Toolkit
- Install CUDA from the [CUDA Toolkit download page](https://developer.nvidia.com/cuda-12-1-0-download-archive) appropriate for your Linux distribution. Follow the installation instructions provided on the NVIDIA website.

### Step 5: Install PyTorch with GPU Support
- Visit the [PyTorch installation guide](https://pytorch.org/get-started/locally/), set preferences for Linux, Conda, and the appropriate CUDA version.
- Use the provided command in the page, such as `conda install pytorch torchvision torchaudio pytorch-cuda=12.1 -c pytorch -c nvidia`, in your terminal.

### Step 6: Download Miner Scripts
- Use Git to clone the miner scripts repository with `git clone https://github.com/heurist-network/miner-release`. Alternatively, download the ZIP from the GitHub page and extract it.
  
### Step 7: Install Dependencies from requirements.txt
- Ensure you're in the Conda environment (`conda activate gpu-3-11`).
- Navigate to the miner-release directory.
- Install dependencies with `pip install -r requirements.txt`.

### Step 8. Configure your Miner ID
Use `.env` in the miner-release folder to set a unique miner_id for each GPU. (Same as Windows guide above. This is very important for tracking your contribution!)

### Step 9. Run the miner program
- Execute the miner script with `python3 sd-miner-v0.0.x.py` (select the latest version) in your terminal. Agree to download model files when prompted.
  
### Additional Linux-Specific Tips:
- Use `screen` or `tmux` to keep the miner running in the background, especially when connected via SSH.

Follow these steps to set up the Heurist Miner on a Linux system, adjusting commands and procedures as necessary for your specific Linux distribution and setup.
