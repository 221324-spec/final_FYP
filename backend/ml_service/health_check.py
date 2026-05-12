"""Health check and environment validation for Recovery Road ML service.

Validates:
- Python version (3.10, 3.11, 3.12 recommended; 3.13+ warnings)
- Core ML dependencies (scikit-learn, numpy, pandas)
- Optional enhancements (transformers, torch, xgboost, lightgbm)
- Model loading and inference capability
- Graceful fallback if any optional dependency is missing

Run as: python -m ml_service.health_check
Or import: from ml_service.health_check import validate_environment, report_status
"""

import sys
from pathlib import Path
from typing import Any

__version__ = "1.0.0"

# Color codes for terminal output
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def _fmt_ok(msg: str) -> str:
    return f"{Colors.GREEN}✓ {msg}{Colors.ENDC}"


def _fmt_warn(msg: str) -> str:
    return f"{Colors.YELLOW}⚠ {msg}{Colors.ENDC}"


def _fmt_err(msg: str) -> str:
    return f"{Colors.RED}✗ {msg}{Colors.ENDC}"


def _fmt_info(msg: str) -> str:
    return f"{Colors.BLUE}ℹ {msg}{Colors.ENDC}"


def _fmt_header(msg: str) -> str:
    return f"\n{Colors.BOLD}{msg}{Colors.ENDC}"


def validate_python_version() -> dict[str, Any]:
    """Check Python version compatibility."""
    major, minor, patch = sys.version_info[:3]
    version_str = f"{major}.{minor}.{patch}"
    platform_str = sys.platform

    issues = []
    warnings = []

    if (major, minor) < (3, 10):
        issues.append(f"Python {version_str} is too old; requires 3.10+")
    elif (major, minor) >= (3, 13):
        warnings.append(f"Python {version_str} may have compatibility issues; test thoroughly")
    elif (major, minor) not in [(3, 10), (3, 11), (3, 12)]:
        warnings.append(f"Python {version_str} not officially tested; use 3.11 preferred")

    if platform_str not in ["win32", "linux", "darwin"]:
        warnings.append(f"Platform {platform_str} is not standard")

    status = "error" if issues else ("warning" if warnings else "ok")
    return {
        "status": status,
        "python_version": version_str,
        "platform": platform_str,
        "issues": issues,
        "warnings": warnings,
    }


def validate_core_dependencies() -> dict[str, Any]:
    """Check core ML dependencies that must work."""
    results = {}

    required_packages = {
        "numpy": {"version": None, "required": True},
        "scipy": {"version": None, "required": True},
        "sklearn": {"import_name": "sklearn", "version": None, "required": True},
        "pandas": {"version": None, "required": True},
        "joblib": {"version": None, "required": True},
    }

    for pkg_name, info in required_packages.items():
        import_name = info.get("import_name", pkg_name)
        try:
            mod = __import__(import_name)
            version = getattr(mod, "__version__", "unknown")
            results[pkg_name] = {
                "available": True,
                "version": version,
                "required": info["required"],
            }
        except ImportError as e:
            results[pkg_name] = {
                "available": False,
                "error": str(e),
                "required": info["required"],
            }

    all_required_ok = all(
        pkg["available"] for pkg in results.values() if pkg["required"]
    )
    return {
        "status": "ok" if all_required_ok else "error",
        "packages": results,
    }


def validate_optional_dependencies() -> dict[str, Any]:
    """Check optional ML enhancements."""
    results = {}

    optional_packages = {
        "torch": "PyTorch (optional; for transformers inference)",
        "transformers": "HuggingFace Transformers (optional; for embeddings)",
        "sentence_transformers": "Sentence Transformers (optional; for embeddings)",
        "xgboost": "XGBoost (optional; for risk scoring)",
        "lightgbm": "LightGBM (optional; lightweight alternative)",
        "opencv": "OpenCV (optional; for emotion service)",
        "deepface": "DeepFace (optional; for emotion detection)",
        "tensorflow": "TensorFlow (optional; for deepface backend)",
        "shap": "SHAP (optional; for explainability)",
    }

    for pkg_name, description in optional_packages.items():
        try:
            if pkg_name == "opencv":
                mod = __import__("cv2")
                pkg_display = "cv2"
            elif pkg_name == "sentence_transformers":
                mod = __import__("sentence_transformers")
                pkg_display = "sentence_transformers"
            else:
                mod = __import__(pkg_name)
                pkg_display = pkg_name

            version = getattr(mod, "__version__", "unknown")
            results[pkg_name] = {
                "available": True,
                "version": version,
                "description": description,
            }
        except ImportError:
            results[pkg_name] = {
                "available": False,
                "description": description,
            }

    return {
        "status": "ok",
        "packages": results,
    }


def validate_model_loading() -> dict[str, Any]:
    """Check if models can be loaded from disk."""
    models_dir = Path(__file__).resolve().parent / "models"
    results = {}

    model_files = {
        "text_risk_classifier.joblib": "Text risk model",
        "emotion_classifier.joblib": "Emotion model",
        "risk_feature_classifier.joblib": "Risk feature model",
        "model_meta.json": "Model metadata",
    }

    for filename, description in model_files.items():
        filepath = models_dir / filename
        exists = filepath.exists()
        results[filename] = {
            "exists": exists,
            "description": description,
            "path": str(filepath),
        }

    all_models_ok = all(r["exists"] for r in results.values())
    return {
        "status": "ok" if all_models_ok else "warning",
        "models_dir": str(models_dir),
        "models": results,
    }


def validate_inference_capability() -> dict[str, Any]:
    """Check if basic inference works."""
    try:
        from ml_models import classify_text, is_ready

        if not is_ready():
            return {
                "status": "warning",
                "message": "Models not loaded; run training first",
                "can_infer": False,
            }

        result = classify_text("I want to relapse")
        if result and "risk" in result:
            return {
                "status": "ok",
                "message": "Inference works",
                "can_infer": True,
                "sample_output": result,
            }
        else:
            return {
                "status": "warning",
                "message": "Inference returned unexpected format",
                "can_infer": False,
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Inference failed: {str(e)}",
            "can_infer": False,
            "error": str(e),
        }


def report_status() -> None:
    """Print comprehensive status report."""
    print(f"{Colors.BOLD}Recovery Road — ML Service Environment Check{Colors.ENDC}")
    print(f"Version: {__version__}\n")

    # Python version
    print(_fmt_header("1. Python Version"))
    py_check = validate_python_version()
    version_str = py_check["python_version"]
    platform_str = py_check["platform"]
    print(f"  Python: {version_str} on {platform_str}")
    if py_check["status"] == "error":
        for issue in py_check["issues"]:
            print(f"  {_fmt_err(issue)}")
    elif py_check["status"] == "warning":
        for warning in py_check["warnings"]:
            print(f"  {_fmt_warn(warning)}")
    else:
        print(f"  {_fmt_ok('Python version supported')}")

    # Core dependencies
    print(_fmt_header("2. Core Dependencies"))
    core_check = validate_core_dependencies()
    for pkg_name, info in core_check["packages"].items():
        if info["available"]:
            ver = info.get("version", "unknown")
            req_str = " (required)" if info["required"] else " (optional)"
            print(f"  {_fmt_ok(f'{pkg_name} {ver}{req_str}')}")
        else:
            req_str = " (required)" if info["required"] else " (optional)"
            err_msg = info.get("error", "not installed")
            status = _fmt_err if info["required"] else _fmt_warn
            print(f"  {status(f'{pkg_name}: {err_msg}{req_str}')}")

    # Optional dependencies
    print(_fmt_header("3. Optional Enhancements"))
    opt_check = validate_optional_dependencies()
    for pkg_name, info in opt_check["packages"].items():
        if info["available"]:
            ver = info.get("version", "unknown")
            desc = info.get("description", "")
            print(f"  {_fmt_ok(f'{desc} ({ver})')}")
        else:
            desc = info.get("description", "")
            print(f"  {_fmt_warn(f'{desc} (not installed; optional)')}")

    # Model files
    print(_fmt_header("4. Model Files"))
    models_check = validate_model_loading()
    models_dir = models_check["models_dir"]
    print(f"  Models directory: {models_dir}")
    for filename, info in models_check["models"].items():
        if info["exists"]:
            print(f"  {_fmt_ok(f'{filename}')}")
        else:
            print(f"  {_fmt_warn(f'{filename} (not found; run training first)')}")

    # Inference capability
    print(_fmt_header("5. Inference Capability"))
    infer_check = validate_inference_capability()
    if infer_check["status"] == "ok":
        print(f"  {_fmt_ok(infer_check['message'])}")
        if "sample_output" in infer_check:
            sample = infer_check["sample_output"]
            risk = sample.get("risk", "?")
            emotion = sample.get("emotion", "?")
            conf = sample.get("confidence", 0)
            print(f"    Sample: risk={risk}, emotion={emotion}, confidence={conf:.2f}")
    elif infer_check["status"] == "warning":
        print(f"  {_fmt_warn(infer_check['message'])}")
    else:
        print(f"  {_fmt_err(infer_check['message'])}")
        if "error" in infer_check:
            print(f"    Error: {infer_check['error']}")

    # Summary
    print(_fmt_header("Summary"))
    py_ok = py_check["status"] != "error"
    core_ok = core_check["status"] == "ok"
    models_ok = models_check["status"] == "ok"
    infer_ok = infer_check["status"] == "ok"

    if py_ok and core_ok and infer_ok:
        print(
            f"  {_fmt_ok('All systems go! ML service is ready.')}"
        )
    elif py_ok and core_ok:
        print(
            f"  {_fmt_warn('Core dependencies OK; models need training or optional deps missing.')}"
        )
    elif py_ok:
        print(
            f"  {_fmt_err('Missing core dependencies; run: pip install -r requirements.txt')}"
        )
    else:
        print(
            f"  {_fmt_err('Python version incompatible or platform unsupported.')}"
        )


def validate_environment() -> bool:
    """Return True if environment is valid for ML operations."""
    py_check = validate_python_version()
    core_check = validate_core_dependencies()
    infer_check = validate_inference_capability()

    return (
        py_check["status"] != "error"
        and core_check["status"] == "ok"
        and infer_check.get("can_infer", False)
    )


if __name__ == "__main__":
    report_status()
    sys.exit(0 if validate_environment() else 1)
