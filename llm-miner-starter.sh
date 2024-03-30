#!/bin/bash

# Configuration variables
DEFAULT_MODEL_ID="TheBloke/OpenHermes-2.5-Mistral-7B-GPTQ"
DEFAULT_QUANTIZATION="gptq"

log_info() {
    # Blue color for informational messages
    echo -e "\033[0;34mINFO: $1\033[0m" >&2
}

log_warning() {
    # Yellow color for warning messages, printed to stderr
    echo -e "\033[0;33mWARNING: $1\033[0m" >&2
}

log_error() {
    # Red color for error messages, printed to stderr
    echo -e "\033[0;31mERROR: $1\033[0m" >&2
}

# Function to check command prerequisites and report all missing dependencies
check_prerequisites() {
    local missing_prerequisites=()
    # Base prerequisites without considering Python venv yet
    local prerequisites=("jq" "wget")

    # Determine the default Python version
    local python_version=$(python3 --version 2>&1 | grep -oP 'Python \K[0-9]+\.[0-9]+')

    # Decide whether to check for python3-venv or python3.8-venv based on Python version
    if [[ "$python_version" =~ ^3\.(8|9|10|11)$ ]]; then
        prerequisites+=("python3-venv")
    else
        prerequisites+=("python3.8-venv")
    fi

    for prerequisite in "${prerequisites[@]}"; do
        # Handle Python venv packages separately
        if [[ "$prerequisite" == "python3-venv" || "$prerequisite" == "python3.8-venv" ]]; then
            if ! dpkg -l | grep -q "$prerequisite"; then
                missing_prerequisites+=("$prerequisite")
            fi
        # Check for the presence of other executable commands
        elif ! command -v "$prerequisite" &> /dev/null; then
            missing_prerequisites+=("$prerequisite")
        fi
    done

    if [ ${#missing_prerequisites[@]} -eq 0 ]; then
        log_info "All prerequisites are satisfied."
    else
        for missing in "${missing_prerequisites[@]}"; do
            if [[ "$missing" == "python3-venv" || "$missing" == "python3.8-venv" ]]; then
                log_error "$missing is not installed but is required. Please install $missing with the following command: sudo apt update && sudo apt install software-properties-common && sudo apt install $missing"
            else
                log_error "$missing is not installed but is required. Please install $missing with the following command: sudo apt update && sudo apt install $missing"
            fi
        done
        exit 1
    fi
}

# Validate internet connectivity to essential services
validate_connectivity() {
    # List of essential URLs to check connectivity
    local urls=("https://huggingface.co")

    for url in "${urls[@]}"; do
        if ! wget --spider -q "$url"; then
            log_error "Unable to connect to $url. Check your internet connection or access to the site."
            exit 1
        else
            log_info "Connectivity to $url verified."
        fi
    done
}

setup_venv_environment() {
    local env_dir="llm-venv"
    local cfg_file="$env_dir/pyvenv.cfg"
    
    # Function to parse the Python version from pyvenv.cfg
    get_python_version_from_venv() {
        local version_line=$(grep 'version = ' "$cfg_file")
        echo "$version_line" | cut -d ' ' -f 3
    }

    if [ -d "$env_dir" ] && [ -f "$cfg_file" ]; then
        local venv_python_version=$(get_python_version_from_venv)
        if [[ "$venv_python_version" =~ ^3\.(8|9|10|11)(\.[0-9]+)?$ ]]; then
            log_info "Virtual environment exists with Python version $venv_python_version, which is within the desired range."
        else
            log_info "Virtual environment detected with Python version $venv_python_version, which is outside the desired range. Recreating environment..."
            rm -rf "$env_dir"
            python3 -m venv "$env_dir"
            log_info "Virtual environment re-created with the current Python version."
        fi
    elif [ ! -d "$env_dir" ]; then
        log_info "Creating a new virtual environment with venv..."
        python3 -m venv "$env_dir"
        log_info "Virtual environment created."
    fi

    source "$env_dir/bin/activate"
    log_info "Virtual environment activated."
}

setup_conda_environment() {
    log_info "Updating package lists..."
    sudo apt-get update -qq >/dev/null 2>&1

    if [ -d "$HOME/miniconda" ]; then
        log_info "Miniconda already installed at $HOME/miniconda. Proceed to create a conda environment."
    else
        log_info "Installing Miniconda..."
        wget --quiet --show-progress --progress=bar:force:noscroll https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh
        bash ~/miniconda.sh -b -p $HOME/miniconda
        export PATH="$HOME/miniconda/bin:$PATH"
        rm ~/miniconda.sh
    fi

    # Ensure Conda is correctly initialized
    source ~/miniconda/bin/activate
    ~/miniconda/bin/conda init bash >/dev/null 2>&1

    # Source .bashrc to update the path for conda, if it exists
    if [ -f "$HOME/.bashrc" ]; then
        log_info "Sourcing .bashrc to update the path for conda"
        source "$HOME/.bashrc"
    elif [ -f "$HOME/.bash_profile" ]; then
        # Fallback for systems that use .bash_profile instead of .bashrc
        log_info "Sourcing .bash_profile to update the path for conda"
        source "$HOME/.bash_profile"
    else
        log_error "Could not find a .bashrc or .bash_profile file to source."
    fi

    # Check if the Conda environment already exists
    if conda info --envs | grep 'llm-venv' > /dev/null; then
        log_info "Conda environment 'llm-venv' already exists. Skipping creation."
    else
        log_info "Creating a virtual environment with Miniconda..."
        # Suppressing the output completely, consider logging at least errors
        conda create -n llm-venv python=3.9 -y --quiet >/dev/null 2>&1
        log_info "Conda virtual environment 'llm-venv' created."
    fi

    conda activate llm-venv
    log_info "Conda virtual environment 'llm-venv' activated."
}

setup_python_environment() {
    log_info "Checking if the current Python version is between 3.8 and 3.11..."

    # Get the major and minor version of the currently active Python
    python_version=$(python3 --version 2>&1 | grep -oP 'Python \K[0-9]+\.[0-9]+')
    
    if [[ "$python_version" =~ ^3\.(8|9|10|11)$ ]]; then
        log_info "Current Python version ($python_version) is within the 3.8 to 3.11 range."
        setup_venv_environment
    else
        log_info "Compatible Python version not found. Current version: $python_version. Proceeding with Miniconda."
        setup_conda_environment
    fi
}

install_with_spinner() {
    local dep=$1
    (
        pip install "$dep" > /dev/null 2>&1
        echo $? > /tmp/install_exit_status.tmp
    ) &

    pid=$! # PID of the pip install process
    spinner="/-\|"

    # Use printf for consistent formatting
    printf "Installing %-20s" "$dep..."

    while kill -0 $pid 2> /dev/null; do
        for i in $(seq 0 3); do
            printf "\b${spinner:i:1}"
            sleep 0.2
        done
    done

    wait $pid
    exit_status=$(cat /tmp/install_exit_status.tmp)
    rm /tmp/install_exit_status.tmp

    if [ $exit_status -eq 0 ]; then
        printf "\b Done.\n"
    else
        printf "\b Failed.\n"
        return 1
    fi
}

# Example usage for your dependency installation function
install_dependencies() {
    log_info "Installing Python dependencies..."
    local dependencies=("vllm" "python-dotenv" "toml" "openai" "triton==2.1.0")

    for dep in "${dependencies[@]}"; do
        if ! install_with_spinner "$dep"; then
            log_error "Failed to install $dep."
            exit 1
        fi
    done

    log_info "All dependencies installed successfully."
}

# Retrieve model size, quantization and name information 
fetchModelDetails() {
    local model_id="$1"
    log_info "Fetching model details for $model_id..."

    local models_json=$(curl -s https://raw.githubusercontent.com/heurist-network/heurist-models/main/models.json)
    if [ -z "$models_json" ]; then
        log_error "Failed to fetch model details from $models_json_url"
        exit 1
    fi

    local model_found=$(echo "$models_json" | jq -r --arg model_id "$model_id" '.[] | select(.hf_id == $model_id)')
    if [ -z "$model_found" ]; then
        log_error "Model ID '$model_id' not found in models.json."
        exit 1
    fi

    # Extracting necessary details
    local size_gb=$(echo "$model_found" | jq -r '.size_gb')
    local quantization=$(echo "$model_found" | jq -r '.type' | grep -q '16b' && echo "None" || echo "gptq")
    local model_name=$(echo "$model_found" | jq -r '.name')
    local revision=$(echo "$model_found" | jq -r '.hf_branch // "None"')


    log_info "Model details: Name=$model_name, Size_GB=$size_gb, Quantization=$quantization, Revision=$revision"
    # Echoing the details for capture by the caller
    echo "$size_gb $quantization $model_name $revision"
}

# Validate GPU VRAM is enough to host expected model
validateVram() {
    local size_gb="$1"
    # Assuming the size_gb is the required VRAM in GB, convert it to MB
    local required_mb=$(echo "$size_gb*1024" | bc)

    log_info "Validating available VRAM against model requirements..."

    # Check if nvidia-smi is available
    if ! command -v nvidia-smi &> /dev/null; then
        log_error "nvidia-smi tool not found. Unable to check available VRAM."
        exit 1
    fi

    # Fetch the available VRAM in MB
    local available_mb=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | awk 'NR==1{print $1}')

    if [ -z "$available_mb" ]; then
        log_error "Failed to fetch available VRAM."
        exit 1
    fi

    log_info "Available VRAM: ${available_mb}MB, Required VRAM: ${required_mb}MB"

    # Compare available and required VRAM
    if [ "$available_mb" -lt "$required_mb" ]; then
        log_error "Insufficient VRAM. Available: ${available_mb}MB, Required: ${required_mb}MB."
        exit 1
    else
        log_info "Sufficient VRAM available. Proceeding..."
    fi
}

getModelId() {
    # Capture the first command-line argument as the model ID
    local model_id="$1"

    # If no model ID was provided, use the default value
    if [ -z "$model_id" ]; then
        log_warning "No model ID provided. Defaulting to $DEFAULT_MODEL_ID" >&2
        model_id=$DEFAULT_MODEL_ID
    fi
    # Return the determined model ID
    echo "$model_id"
}

main() {
    log_info "Starting script execution..."

    check_prerequisites
    validate_connectivity
    setup_python_environment
    install_dependencies

    # Fetch model details including the model ID, required VRAM size, quantization method, and model name
    model_id=$(getModelId "$1")
    read -r size_gb quantization model_name revision < <(fetchModelDetails "$model_id")

    # Check if the model details were not properly fetched
    if [ -z "$size_gb" ] || [ -z "$quantization" ] || [ -z "$model_name" ] || [ -z "$revision" ]; then
        log_error "Failed to fetch model details. Exiting."
        exit 1
    fi

    # Validate if the system has enough VRAM for the model
    validateVram "$size_gb"

    # Assuming all validations passed, proceed to execute the Python script with the model details
    log_info "Executing Python script with model ID: $model_id, Quantization: $quantization, Model Name: $model_name and Revision: $revision"
    local python_script=$(ls llm-miner-*.py | head -n 1)
    if [[ -n "$python_script" ]]; then
        python "$python_script" "$model_id" "$quantization" "$model_name" "$revision"
        log_info "Python script executed successfully."
    else
        log_error "No Python script matching 'llm-miner-*.py' found."
        exit 1
    fi

    log_info "Script execution completed."
}

main "$@"
