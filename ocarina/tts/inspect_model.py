"""
Does mlx-audio know this kind of model? Run as a child process (python -m ocarina.tts.inspect_model <model_type> <repo>):
importing the model code is heavy and loads MLX, which the app itself should not do. Prints one JSON line.
"""

import json
import sys


def inspect(model_type, repo):
    "{known, module, problem}: whether mlx-audio has code for this model type (by its declared type or its name)."
    from mlx_audio.utils import get_model_name_parts  # pylint: disable=import-outside-toplevel
    from mlx_audio.tts.utils import get_model_and_args  # pylint: disable=import-outside-toplevel

    try:
        module, resolved = get_model_and_args(model_type or "", get_model_name_parts(repo))
        return {"known": True, "module": resolved or getattr(module, "__name__", ""), "problem": None}
    except ModuleNotFoundError as e:
        # The model's code exists but needs a package Ocarina does not have (for example torch).
        return {"known": True, "module": model_type, "problem": f"needs the Python package “{e.name}”"}
    except ValueError as e:
        if "not supported" in str(e):  # mlx-audio's own answer for a model type it has no code for
            return {"known": False, "module": None, "problem": str(e)[:200]}
        return {"known": None, "module": None, "problem": "Could not check this automatically."}
    except Exception:  # pylint: disable=broad-exception-caught
        # Anything else (a lookup that needs the internet, for instance) means we cannot tell, not that it is unsupported.
        return {"known": None, "module": None, "problem": "Could not check this automatically."}


if __name__ == "__main__":
    print(json.dumps(inspect(sys.argv[1] if len(sys.argv) > 1 else "", sys.argv[2] if len(sys.argv) > 2 else "")))
