BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)


def string_colour(text: str, colour: int=WHITE) -> str:
    """
    Create string text in a particular colour to the terminal.
    Args:
        text (str): The text to colourise.
        colour (int): The colour to use for the text. Default is WHITE.
    Returns:
        str: The colourised text.
    """
    seq = "\x1b[1;%dm" % (30 + colour) + text + "\x1b[0m"
    return seq


if __name__ == "__main__":
    for color in [RED, GREEN, BLUE, CYAN]:
        msg = string_colour(f"Testing color {color}", color)
        print(msg)
