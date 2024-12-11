#!/bin/bash

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
    local prerequisites=("jq" "wget" "bc")

    # Check if running in a Conda environment
    if [[ -z "${CONDA_DEFAULT_ENV}" ]]; then
        # Only check for python venv if not in Conda environment
        local python_version=$(python3 --version 2>&1 | grep -oP 'Python \K[0-9]+\.[0-9]+')
        if [[ "$python_version" =~ ^3\.(8|9|10|11)$ ]]; then
            prerequisites+=("python3-venv")
        else
            prerequisites+=("python3.8-venv")
        fi
    fi

    for prerequisite in "${prerequisites[@]}"; do
        if [[ "$prerequisite" == "python3-venv" || "$prerequisite" == "python3.8-venv" ]]; then
            if [[ -z "${CONDA_DEFAULT_ENV}" ]]; then
                if ! dpkg -l | grep -q "$prerequisite"; then
                    missing_prerequisites+=("$prerequisite")
                fi
            else
                log_warning "$prerequisite check skipped in Conda environment."
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
                log_error "$missing is not installed but is required. Please install $missing with the following command: sudo apt update && sudo apt upgrade && sudo apt install software-properties-common && sudo add-apt-repository ppa:deadsnakes/ppa && sudo apt install $missing"
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

install_with_spinner() {
    local dep=$1
    local log_file="/tmp/pip_install_log_${dep// /_}.txt"
    local status_file="/tmp/install_exit_status_${dep// /_}.tmp"

    (
        pip install "$dep" > "$log_file" 2>&1
        echo $? > "$status_file"
    ) &

    pid=$! # PID of the pip install process
    spinner="/-\|"

    printf "Installing %-20s" "$dep..."

    while kill -0 $pid 2> /dev/null; do
        for i in $(seq 0 3); do
            printf "\b${spinner:i:1}"
            sleep 0.2
        done
    done

    wait $pid

    if [ -f "$status_file" ]; then
        exit_status=$(cat "$status_file")
        rm -f "$status_file"
    else
        exit_status=1
        echo "Warning: Status file not found. Assuming installation failed."
    fi

    if [ "$exit_status" -eq 0 ]; then
        printf "\b Done.\n"
    else
        printf "\b Failed.\n"
        echo "Installation of $dep failed. Error details:"
        [ -f "$log_file" ] && cat "$log_file"
    fi

    # Remove log file if it exists
    [ -f "$log_file" ] && rm -f "$log_file"

    return "$exit_status"
}

setup_conda_environment() {
    log_info "Updating package lists..."
    sudo apt-get update -qq >/dev/null 2>&1

    if [ -d "$HOME/miniconda" ]; then
        log_info "Miniconda already installed at $HOME/miniconda. Proceeding to create/update conda environment."
    else
        log_info "Installing Miniconda..."
        wget --quiet --show-progress --progress=bar:force:noscroll https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh
        bash ~/miniconda.sh -b -p $HOME/miniconda
        export PATH="$HOME/miniconda/bin:$PATH"
        rm ~/miniconda.sh
    fi

    # Ensure Conda is correctly initialized
    source $HOME/miniconda/bin/activate
    $HOME/miniconda/bin/conda init bash >/dev/null 2>&1

    # Source .bashrc to update the path for conda, if it exists
    if [ -f "$HOME/.bashrc" ]; then
        log_info "Sourcing .bashrc to update the path for conda"
        source "$HOME/.bashrc"
    elif [ -f "$HOME/.bash_profile" ]; then
        log_info "Sourcing .bash_profile to update the path for conda"
        source "$HOME/.bash_profile"
    else
        log_error "Could not find a .bashrc or .bash_profile file to source."
    fi

    # Check if the Conda environment already exists
    if conda env list | grep -q "$HOME/miniconda/envs/llm-venv"; then
        log_info "Conda environment 'llm-venv' exists. Checking if it's valid..."
        if conda run -n llm-venv python --version >/dev/null 2>&1; then
            log_info "Conda environment 'llm-venv' is valid. Activating..."
        else
            log_warning "Conda environment 'llm-venv' exists but appears to be invalid. Removing and recreating..."
            conda env remove -n llm-venv -y
            conda create -n llm-venv python=3.11 -y --quiet
        fi
    else
        log_info "Creating a new conda environment 'llm-venv'..."
        conda create -n llm-venv python=3.11 -y --quiet
    fi

    # Activate the environment
    conda activate llm-venv
    if [ $? -ne 0 ]; then
        log_error "Failed to activate Conda environment. Please check your Conda installation."
        exit 1
    fi
    log_info "Conda virtual environment 'llm-venv' activated."

    # Ensure pip is installed in the environment
    if ! command -v pip &> /dev/null; then
        log_info "Installing pip in the Conda environment..."
        conda install pip -y
        if [ $? -ne 0 ]; then
            log_error "Failed to install pip. Please check your Conda installation."
            exit 1
        fi
    fi
}

install_dependencies() {
    log_info "Installing Python dependencies..."
    local dependencies=("vllm >= 0.6.3" "python-dotenv" "toml" "openai >= 1.40.0" "triton" "wheel" "packaging" "psutil" "web3" "mnemonic" "prettytable" "ray")

    # Ensure Conda environment is activated
    if [ -z "$CONDA_PREFIX" ]; then
        log_error "Conda environment is not activated. Attempting to activate..."
        conda activate llm-venv
        if [ $? -ne 0 ]; then
            log_error "Failed to activate Conda environment. Please check your Conda installation."
            exit 1
        fi
    fi

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
    local heurist_model_id="$1"
    log_info "Fetching model details for $heurist_model_id..."

    local models_json=$(curl -s https://raw.githubusercontent.com/heurist-network/heurist-models/main/models.json)
    if [ -z "$models_json" ]; then
        log_error "Failed to fetch model details from $models_json_url"
        exit 1
    fi

    local model_found=$(echo "$models_json" | jq -r --arg heurist_model_id "$heurist_model_id" '.[] | select(.name == $heurist_model_id)')
    if [ -z "$model_found" ]; then
        log_error "Heurist Model ID '$heurist_model_id' not found in models.json."
        exit 1
    fi

    # Extracting necessary details
    local size_gb=$(echo "$model_found" | jq -r '.size_gb')
    local quantization=$(echo "$model_found" | jq -r '.type' | grep -q '16b' && echo "None" || echo "gptq")
    local hf_model_id=$(echo "$model_found" | jq -r '.hf_id')
    local revision=$(echo "$model_found" | jq -r '.hf_branch // "None"')
    local tool_call_parser=$(echo "$model_found" | jq -r '.tool_call_parser // "None"')

    log_info "Model details: HF_ID=$hf_model_id, Size_GB=$size_gb, Quantization=$quantization, Revision=$revision, Tool Call Parser=$tool_call_parser"
    # Echoing the details for capture by the caller
    echo "$size_gb $quantization $hf_model_id $revision $tool_call_parser"
}

validateMinerId() {
    local miner_id=$1
    local config_file=$2
    local abi_file=$3

    # Call the WalletGenerator class directly
    python -c "
from auth.generator import WalletGenerator

config_file = '$config_file'
abi_file = '$abi_file'
miner_id = '$miner_id'

wallet_generator = WalletGenerator(config_file, abi_file)
wallet_generator.validate_miner_keys([miner_id])
"
    local exit_code=$?

    if [ $exit_code -ne 0 ]; then
        log_error "Wallet validation failed for Miner ID: $miner_id"
        exit 1
    fi
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

    # Initialize total available VRAM
    local total_available_mb=0
    # Iterate over each GPU ID
    IFS=',' read -ra gpu_id_array <<< "$gpu_ids"
    for gpu_id in "${gpu_id_array[@]}"; do
        # Fetch the available VRAM in MB for each GPU
        local available_mb=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits --id="$gpu_id")

        if [ -z "$available_mb" ]; then
            log_error "Failed to fetch available VRAM for GPU $gpu_id."
            exit 1
        fi

        # Add the available VRAM to the total
        total_available_mb=$((total_available_mb + available_mb))
    done

    log_info "Total available VRAM: ${total_available_mb}MB, Required VRAM: ${required_mb}MB"

    # Compare total available VRAM and required VRAM
    if [ "$total_available_mb" -lt "$required_mb" ]; then
        log_error "Insufficient VRAM. Total available: ${total_available_mb}MB, Required: ${required_mb}MB."
        exit 1
    fi

    # Determine GPU memory utilization based on model name and available VRAM
    if [[ "$heurist_model_id" == *"mixtral-8x7b-gptq"* ]] && [ "$total_available_mb" -gt 35000 ]; then
        local gpu_memory_util=$(echo "scale=2; (35000-1000)/$total_available_mb" | bc)
    elif [[ "$heurist_model_id" == *"70b"* ]] && [ "$total_available_mb" -gt 44000 ]; then
        local gpu_memory_util=$(echo "scale=2; (44000-1000)/$total_available_mb" | bc)
    elif [[ "$heurist_model_id" == *"8b"* ]] && [ "$total_available_mb" -gt 21000 ]; then
        local gpu_memory_util=$(echo "scale=2; (21000-1000)/$total_available_mb" | bc)
    else
        local gpu_memory_util=$(echo "scale=2; (12000-1000)/$total_available_mb" | bc) # Default value or handle other cases as needed
    fi

    # Output the gpu_memory_util value
    printf "%.2f" "$gpu_memory_util"
}

getModelId() {
    local heurist_model_id="$1"

    # If no model ID was provided, exit with an error message
    if [ -z "$heurist_model_id" ]; then
        log_error "No model ID provided. Please provide a model ID. See https://docs.heurist.ai/integration/supported-models for supported models."
        exit 1
    fi
    # Return the determined model ID
    echo "$heurist_model_id"
}

main() {
    log_info "Starting script execution..."

    check_prerequisites
    validate_connectivity
    setup_conda_environment
    install_dependencies

    # Default values for the new arguments
    local miner_id_index=0
    local port=8000
    local gpu_ids="0" # User can specify GPUs to use. Example: "0,1" for GPUs 0 and 1.
    local skip_signature=false 

    # Fetch model details including the model ID, required VRAM size, quantization method, and model name
    heurist_model_id=$(getModelId "$1") || exit 1
    read -r size_gb quantization hf_model_id revision tool_call_parser < <(fetchModelDetails "$heurist_model_id")

    shift 1
    # Parse additional arguments
    while (( "$#" )); do
        case "$1" in
            --miner-id-index)
                miner_id_index=$2
                shift 2
                ;;
            --port)
                port=$2
                shift 2
                ;;
            --gpu-ids)
                gpu_ids=$2
                shift 2
                ;;
            --skip-signature)
                skip_signature=true
                shift
                ;;
            *) # unrecognized argument
                break
                ;;
        esac
    done

    # Extract the miner ID from the .env file based on the miner_id_index
    miner_id=$(sed -n "s/^MINER_ID_$miner_id_index=//p" .env)
    # Validate the miner ID only if skip_signature is false
    if ! $skip_signature; then
        validateMinerId "$miner_id" "config.toml" "auth/abi.json"
    fi

    # Check if the model details were not properly fetched
    if [ -z "$size_gb" ] || [ -z "$quantization" ] || [ -z "$hf_model_id" ] || [ -z "$revision" ]; then
        log_error "Failed to fetch model details. Exiting."
        exit 1
    fi

    # Validate if the system has enough VRAM for the model
    gpu_memory_util=$(validateVram "$size_gb")
    log_info "GPU Memory Utilization ratio for vllm: $gpu_memory_util"

    # Assuming all validations passed, proceed to execute the Python script with the model details
    log_info "Executing Python script with Heurist model ID: $heurist_model_id, Quantization: $quantization, HuggingFace model ID: $hf_model_id, Revision: $revision, Tool Call Parser: $tool_call_parser, Miner ID Index: $miner_id_index, Port: $port, GPU IDs: $gpu_ids"
    local python_script=$(ls llm-miner.py | head -n 1)
    if [[ -n "$python_script" ]]; then
        python "$python_script" "$hf_model_id" "$quantization" "$heurist_model_id" $gpu_memory_util "$revision" "$miner_id_index" "$port" "$gpu_ids" "$skip_signature" "$tool_call_parser"
        log_info "Python script executed successfully."
    else
        log_error "No Python script matching 'llm-miner.py' found."
        exit 1
    fi

    log_info "Script execution completed."
}

main "$@"
