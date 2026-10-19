"""Console countdown timer."""

import time


def countdown(seconds, sleep_function=time.sleep, output_function=print):
    """Display a countdown in MM:SS format and announce completion."""
    while seconds > 0:
        minutes, remaining_seconds = divmod(seconds, 60)
        time_text = "{:02d}:{:02d}".format(minutes, remaining_seconds)
        output_function(time_text, end="\r", flush=True)
        sleep_function(1)
        seconds -= 1

    output_function("00:00")
    output_function("Fire in the hole!!")


def get_duration():
    """Read and validate a non-negative countdown duration from the user."""
    while True:
        user_input = input("Enter countdown duration in seconds: ").strip()
        try:
            seconds = int(user_input)
        except ValueError:
            print("Please enter a whole number of seconds.")
            continue

        if seconds < 0:
            print("Duration cannot be negative.")
            continue
        return seconds


if __name__ == "__main__":
    countdown(get_duration())