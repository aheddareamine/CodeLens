import fire

from src.cli import Cli


if __name__ == "__main__":
    try:
        fire.Fire(Cli)
    except KeyboardInterrupt:
        # Ctrl+C during a long command: stop cleanly, no traceback
        print("\nInterrupted")
    except Exception as error:
        # last safety net: an error we did not expect is printed on one
        # line instead of a traceback (the subject forbids crashes)
        print(f"Error: {error}")
