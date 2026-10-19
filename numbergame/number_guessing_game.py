"""Command-line number guessing game."""

import random


LOWEST_NUMBER = 1
HIGHEST_NUMBER = 100
MAX_ATTEMPTS = 7


def play_game(
    target_number=None,
    input_function=input,
    output_function=print,
):
    """Run one game and return True for a win or False for a loss."""
    if target_number is None:
        target_number = random.randint(LOWEST_NUMBER, HIGHEST_NUMBER)

    attempts = 0
    output_function(
        f"Guess the number between {LOWEST_NUMBER} and {HIGHEST_NUMBER}. "
        f"You have {MAX_ATTEMPTS} attempts."
    )

    while attempts < MAX_ATTEMPTS:
        try:
            guess = int(input_function(f"Attempt {attempts + 1}: "))
        except ValueError:
            output_function("Invalid input. Enter a whole number from 1 to 100.")
            continue

        if not LOWEST_NUMBER <= guess <= HIGHEST_NUMBER:
            output_function("Invalid input. Enter a number from 1 to 100.")
            continue

        attempts += 1

        if guess == target_number:
            output_function(f"Congratulations! You guessed the number in {attempts} attempts.")
            return True

        if guess < target_number:
            output_function("Too Low")
        else:
            output_function("Too High")

    output_function(f"Game over. The correct number was {target_number}.")
    return False


if __name__ == "__main__":
    play_game()