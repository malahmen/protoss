# general purpose classes and functions
import contextlib 

class ProcessingError(Exception):
    """Custom exception for processing errors"""
    pass

@contextlib.contextmanager
def suppress_stderr():
    """Suppress standard output errors"""
    with open(os.devnull, "w") as devnull:
        old_stderr = sys.stderr
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stderr = old_stderr

def json_to_text(obj, indent=0):
    """Convert a JSON object to a text string"""
    if isinstance(obj, dict):
        return "\n".join(f"{'  ' * indent}{k}: {json_to_text(v, indent + 1)}" for k, v in obj.items())
    elif isinstance(obj, list):
        return "\n".join(f"{'  ' * indent}- {json_to_text(item, indent + 1)}" for item in obj)
    else:
        return str(obj)