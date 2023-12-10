import curses
import time


def main(stdscr):
    curses.use_default_colors()
    curses.curs_set(0)  # Hide the cursor
    stdscr.clear()

    # Print info on the top right corner
    stdscr.addstr(0, curses.COLS - 20, "Press q to quit")

    # print line for the bottom border
    stdscr.hline(curses.LINES - 1, 0, curses.ACS_HLINE, curses.COLS)

    # Other parts of your code go here

    stdscr.refresh()
    stdscr.getch()  # Wait for a key press


curses.wrapper(main)
