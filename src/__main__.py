import fire

from src.cli import Cli


if __name__ == "__main__":
    try:
        fire.Fire(Cli)
    except KeyboardInterrupt:
        # Ctrl+C during a long command: stop cleanly, no traceback
        print("\nInterrupted")
