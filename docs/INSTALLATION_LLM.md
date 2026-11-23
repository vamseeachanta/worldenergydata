# LLM Dependencies Installation Guide

This guide explains how to install and configure Large Language Model (LLM) dependencies for WorldEnergyData.

## Overview

The LLM functionality provides advanced natural language processing and analysis capabilities for energy data. This includes:
- Text analysis of regulatory documents
- Production report summarization
- Field analysis recommendations
- Data extraction from unstructured sources

## System Requirements

### Minimum Requirements

- **RAM**: 8 GB (16 GB recommended)
- **Disk Space**: 5 GB free space (for models and caching)
- **Python**: 3.9 or higher
- **OS**: Linux, macOS, or Windows

### Recommended Requirements

- **RAM**: 16 GB or more
- **Disk Space**: 10 GB or more
- **GPU**: NVIDIA GPU with CUDA support (optional, for faster inference)
- **VRAM**: 4 GB+ (if using GPU)

## Installation Options

### Option 1: Install with pip

```bash
# Install base package
pip install worldenergydata

# Install with LLM support
pip install worldenergydata[llm]
```

### Option 2: Install with UV (Recommended)

```bash
# Install base package
uv add worldenergydata

# Install with LLM support
uv add worldenergydata --extra llm

# Or install from local source
uv pip install -e ".[llm]"
```

### Option 3: Manual Installation

If you prefer to install dependencies manually:

```bash
# Core LLM dependencies
pip install transformers>=4.35.0
pip install torch>=2.0.0
pip install sentencepiece>=0.1.99
pip install accelerate>=0.25.0
```

## GPU vs CPU Considerations

### CPU-Only Installation

For CPU-only usage (slower but works everywhere):

```bash
# Install PyTorch CPU version first
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Then install other LLM dependencies
pip install transformers sentencepiece accelerate
```

**Performance**: CPU inference is 5-10x slower than GPU, but sufficient for batch processing and small-scale analysis.

### GPU Installation (NVIDIA CUDA)

For NVIDIA GPU acceleration (recommended for production use):

#### Prerequisites

1. **Install NVIDIA Drivers**
   - Check driver version: `nvidia-smi`
   - Minimum: Driver version 450+ for CUDA 11.0

2. **Install CUDA Toolkit** (Optional - PyTorch includes CUDA runtime)
   - Download from: https://developer.nvidia.com/cuda-downloads
   - Recommended: CUDA 11.8 or 12.1

3. **Verify GPU**
   ```bash
   nvidia-smi
   # Should show your GPU and driver version
   ```

#### Installation

```bash
# Install PyTorch with CUDA support
# For CUDA 11.8
pip install torch --index-url https://download.pytorch.org/whl/cu118

# For CUDA 12.1
pip install torch --index-url https://download.pytorch.org/whl/cu121

# Install other dependencies
pip install transformers sentencepiece accelerate
```

#### Verify GPU Installation

```python
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA version: {torch.version.cuda}")
print(f"GPU count: {torch.cuda.device_count()}")
if torch.cuda.is_available():
    print(f"GPU name: {torch.cuda.get_device_name(0)}")
```

## Disk Space Management

### Model Storage

Models are cached in:
- **Linux/macOS**: `~/.cache/huggingface/`
- **Windows**: `C:\Users\<username>\.cache\huggingface\`

### Managing Cache

```bash
# Check cache size
du -sh ~/.cache/huggingface/

# Clear cache (WARNING: Models will re-download)
rm -rf ~/.cache/huggingface/transformers/
```

### Pre-download Models

To avoid runtime downloads:

```python
from transformers import AutoTokenizer, AutoModel

# Pre-download a model
model_name = "bert-base-uncased"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name)
```

## Memory Optimization

### For Low-RAM Systems (8 GB)

```python
# Use smaller models
from transformers import AutoTokenizer, AutoModel

# Instead of large models, use smaller variants
model_name = "distilbert-base-uncased"  # ~250 MB vs 500 MB for BERT

# Load with lower precision
model = AutoModel.from_pretrained(
    model_name,
    torch_dtype="auto",  # Automatic mixed precision
    low_cpu_mem_usage=True
)
```

### For High-RAM Systems (16 GB+)

```python
# Can use larger models
model_name = "bert-large-uncased"  # ~1.3 GB

# Enable model parallelism if needed
from accelerate import init_empty_weights, load_checkpoint_and_dispatch

with init_empty_weights():
    model = AutoModel.from_pretrained(model_name)

model = load_checkpoint_and_dispatch(
    model,
    "path/to/checkpoint",
    device_map="auto"
)
```

## Troubleshooting

### Installation Issues

#### Issue: "RuntimeError: CUDA out of memory"

**Solution**: Reduce batch size or use CPU inference

```python
# Reduce batch size
batch_size = 1  # Instead of 8 or 16

# Or force CPU usage
device = torch.device("cpu")
model.to(device)
```

#### Issue: "Could not find a version that satisfies the requirement torch"

**Solution**: Update pip and try again

```bash
pip install --upgrade pip setuptools wheel
pip install torch
```

#### Issue: "ImportError: cannot import name 'AutoModel'"

**Solution**: Reinstall transformers

```bash
pip uninstall transformers
pip install transformers>=4.35.0
```

### Performance Issues

#### Slow Loading Times

**Solution**: Use model caching

```python
import os
os.environ["TRANSFORMERS_CACHE"] = "/path/to/fast/storage"
```

#### High Memory Usage

**Solution**: Clear unused models from memory

```python
import torch
import gc

# After using a model
del model
gc.collect()
torch.cuda.empty_cache()  # If using GPU
```

### Compatibility Issues

#### Issue: Version conflicts with existing packages

**Solution**: Create isolated environment

```bash
# Using venv
python -m venv llm_env
source llm_env/bin/activate  # Linux/macOS
# or
llm_env\Scripts\activate  # Windows

# Using conda
conda create -n llm_env python=3.11
conda activate llm_env

# Install dependencies
pip install worldenergydata[llm]
```

## Testing Installation

### Basic Test

```python
import torch
import transformers

print(f"PyTorch version: {torch.__version__}")
print(f"Transformers version: {transformers.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
```

### Complete Test

```python
from transformers import pipeline

# Test text classification
classifier = pipeline("sentiment-analysis", device=0 if torch.cuda.is_available() else -1)
result = classifier("This offshore field has excellent production performance")
print(f"Test result: {result}")
```

## Environment Variables

### Optional Configuration

```bash
# Set cache directory
export TRANSFORMERS_CACHE=/path/to/cache

# Disable symlinks (Windows)
export TRANSFORMERS_CACHE_DIR=/path/to/cache
export HF_HOME=/path/to/cache

# Offline mode (use cached models only)
export TRANSFORMERS_OFFLINE=1

# Reduce verbosity
export TRANSFORMERS_VERBOSITY=error
```

## Platform-Specific Notes

### Linux

- Ensure proper CUDA driver installation
- May need to install system libraries: `sudo apt-get install build-essential`

### macOS

- Apple Silicon (M1/M2): PyTorch has native support
- Use Metal Performance Shaders (MPS) for acceleration:
  ```python
  device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
  ```

### Windows

- Install Visual C++ Redistributable for PyTorch
- Use WSL2 for better Linux compatibility
- Prefer Windows Terminal for better console output

## Next Steps

After successful installation:

1. **Read the documentation**: Check `docs/LLM_USAGE.md` for usage examples
2. **Explore examples**: See `examples/llm/` directory for sample code
3. **Configure models**: Review `config/llm/` for model configuration options
4. **Run tests**: Execute `pytest tests/llm/` to verify installation

## Getting Help

If you encounter issues not covered here:

1. Check the [GitHub Issues](https://github.com/username/worldenergydata/issues)
2. Review [PyTorch Installation Guide](https://pytorch.org/get-started/locally/)
3. Check [Transformers Documentation](https://huggingface.co/docs/transformers)
4. Create a new issue with:
   - Your system configuration (OS, Python version, GPU)
   - Installation method used
   - Complete error message
   - Output of `pip list | grep -E "torch|transformers"`

## References

- [PyTorch Official Installation](https://pytorch.org/get-started/locally/)
- [Hugging Face Transformers](https://huggingface.co/docs/transformers)
- [Accelerate Library](https://huggingface.co/docs/accelerate)
- [CUDA Installation Guide](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/)
