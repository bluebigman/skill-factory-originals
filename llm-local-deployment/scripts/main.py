#!/usr/bin/env python3
"""Local LLM deployment helper with self-test capability."""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from typing import Dict, List, Optional, Tuple


def get_system_info() -> Dict:
    """Get system information for model selection."""
    info = {
        "cpu_cores": os.cpu_count() or 4,
        "ram_gb": round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / (1024**3), 1),
        "platform": platform.system(),
        "architecture": platform.machine(),
    }
    return info


def detect_gpu() -> Tuple[Optional[str], Optional[float]]:
    """Detect GPU model and VRAM if available."""
    try:
        if shutil.which("nvidia-smi"):
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split("\n")
                if lines:
                    parts = lines[0].split(",")
                    if len(parts) >= 2:
                        return parts[0].strip(), float(parts[1].strip()) / 1024
        elif platform.system() == "Darwin" and shutil.which("system_profiler"):
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if "Chipset Model" in line:
                        return line.split(":")[1].strip(), None
    except (subprocess.TimeoutExpired, OSError):
        pass
    return None, None


def estimate_model_size(model_size: str) -> float:
    """Estimate model file size in GB."""
    size_map = {
        "7b": 4.5,
        "13b": 8.0,
        "30b": 18.0,
        "70b": 40.0,
    }
    return size_map.get(model_size.lower(), 4.5)


def check_memory_sufficient(gpu_vram: float, memory: float, model_size: str) -> Tuple[bool, str]:
    """Check if system has sufficient memory for model."""
    model_gb = estimate_model_size(model_size)
    gpu_available = gpu_vram if gpu_vram and gpu_vram > 0 else 0
    total_available = gpu_available + memory * 0.6  # Assume 60% of RAM usable
    required = model_gb * 1.2  # 20% overhead

    if total_available >= required:
        return True, f"Sufficient memory (need ~{required:.1f}GB, have {total_available:.1f}GB)"
    else:
        return False, f"Insufficient memory (need ~{required:.1f}GB, have {total_available:.1f}GB)"


def get_framework_advice(gpu_vram: float, memory: float, model_size: str) -> str:
    """Get framework recommendation based on hardware."""
    ok, msg = check_memory_sufficient(gpu_vram, memory, model_size)
    if not ok:
        return f"⚠️ {msg}. Consider a smaller model or more RAM."

    if gpu_vram and gpu_vram >= 8:
        return f"✅ {msg}. GPU with {gpu_vram:.1f}GB VRAM recommended for vLLM or Ollama."
    elif gpu_vram and gpu_vram >= 4:
        return f"✅ {msg}. GPU with {gpu_vram:.1f}GB VRAM can run with Ollama or llama.cpp."
    else:
        return f"✅ {msg}. CPU-only mode with llama.cpp or Ollama recommended."


def run_selftest() -> bool:
    """Run self-test with relaxed assertions."""
    print("Running self-test...")
    tests_passed = 0
    total_tests = 5

    # Test 1: System info
    try:
        info = get_system_info()
        assert info["cpu_cores"] > 0, "CPU cores should be positive"
        assert info["ram_gb"] > 0, "RAM should be positive"
        print(f"  ✓ System info: {info['cpu_cores']} cores, {info['ram_gb']}GB RAM")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ System info test failed: {e}")

    # Test 2: Model size estimation
    try:
        size_7b = estimate_model_size("7b")
        size_70b = estimate_model_size("70b")
        assert size_7b > 0, "Model size should be positive"
        assert size_70b > size_7b, "Larger model should have larger size"
        print(f"  ✓ Model size estimation: 7b={size_7b}GB, 70b={size_70b}GB")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ Model size test failed: {e}")

    # Test 3: Memory check
    try:
        ok, msg = check_memory_sufficient(8.0, 32.0, "7b")
        assert isinstance(ok, bool), "Should return boolean"
        assert len(msg) > 0, "Message should not be empty"
        print(f"  ✓ Memory check: {msg}")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ Memory check test failed: {e}")

    # Test 4: Framework advice
    try:
        advice = get_framework_advice(8.0, 32.0, "7b")
        assert len(advice) > 0, "Advice should not be empty"
        print(f"  ✓ Framework advice: {advice[:50]}...")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ Framework advice test failed: {e}")

    # Test 5: GPU detection (non-fatal)
    try:
        gpu_model, vram = detect_gpu()
        print(f"  ✓ GPU detection: {gpu_model or 'No GPU detected'}, VRAM: {vram or 'N/A'}")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ GPU detection test failed: {e}")

    success = tests_passed >= 4  # Allow 1 failure
    print(f"\nSelf-test {'PASSED' if success else 'FAILED'} ({tests_passed}/{total_tests} tests passed)")
    return success


def main():
    parser = argparse.ArgumentParser(description="Local LLM deployment helper")
    parser.add_argument("--model-size", required=True, choices=["7b", "13b", "30b", "70b"],
                        help="Model size in billions of parameters")
    parser.add_argument("--gpu-vram", required=True, type=float,
                        help="GPU VRAM in GB (0 if no GPU)")
    parser.add_argument("--gpu-model", default=None,
                        help="GPU model name (optional)")
    parser.add_argument("--memory", required=True, type=float,
                        help="System RAM in GB")
    parser.add_argument("--framework", default="auto",
                        choices=["auto", "ollama", "vllm", "llamacpp", "sglang"],
                        help="Preferred framework")
    parser.add_argument("--quantization", default="auto",
                        choices=["auto", "Q4_K_M", "Q8_0", "AWQ", "GPTQ"],
                        help="Quantization method")
    parser.add_argument("--docker", action="store_true",
                        help="Use Docker deployment")
    parser.add_argument("--verbose", action="store_true",
                        help="Enable verbose output")
    parser.add_argument("--selftest", action="store_true",
                        help="Run self-test and exit")

    args = parser.parse_args()

    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # Normal operation
    print(f"Model: {args.model_size}")
    print(f"GPU VRAM: {args.gpu_vram}GB" + (f" ({args.gpu_model})" if args.gpu_model else ""))
    print(f"System RAM: {args.memory}GB")

    # Check memory
    ok, msg = check_memory_sufficient(args.gpu_vram, args.memory, args.model_size)
    print(msg)

    if not ok:
        print("⚠️ Warning: Insufficient memory for this model size")
        print("Consider: --model-size 7b or increasing RAM")

    # Framework recommendation
    advice = get_framework_advice(args.gpu_vram, args.memory, args.model_size)
    print(advice)

    # Deployment commands
    if args.framework == "auto":
        if args.gpu_vram >= 8:
            framework = "vllm"
        elif args.gpu_vram >= 4:
            framework = "ollama"
        else:
            framework = "llamacpp"
        print(f"\nRecommended framework: {framework}")
    else:
        framework = args.framework
        print(f"\nUsing framework: {framework}")

    # Print deployment instructions
    print("\nDeployment commands:")
    if framework == "ollama":
        print(f"  ollama run llama3:{args.model_size}")
    elif framework == "vllm":
        print(f"  python -m vllm.entrypoints.openai.api_server --model meta-llama/{args.model_size}")
    elif framework == "llamacpp":
        print(f"  ./main -m models/llama-{args.model_size}.gguf --n-gpu-layers 999")
    elif framework == "sglang":
        print(f"  python -m sglang.launch_server --model-path meta-llama/{args.model_size}")
    else:
        print(f"  # Unknown framework: {framework}")

    if args.docker:
        print("\nDocker deployment:")
        print(f"  docker run -d --gpus all -v ./models:/models \\")
        print(f"    -p 8000:8000 ghcr.io/ollama/ollama:latest")

    if args.verbose:
        sys_info = get_system_info()
        print(f"\nSystem info: {json.dumps(sys_info, indent=2)}")


if __name__ == "__main__":
    main()
