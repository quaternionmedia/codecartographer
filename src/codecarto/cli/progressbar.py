class ProgressBar:
    """A simple progress bar for Python."""

    def __init__(self, total, prefix = '', suffix = '', bar_length = 50, percent_decimals = 0, fill_char = '█', print_end = "\r", line_number = -1, extra_msg = ""):
        """Initializes the progress bar.
        
        Parameters:
        -----------
        total (int): 
            Total number of iterations.
        prefix (str, Default: ""):
            Prefix string.
        suffix (str, Default: ""):
            Suffix string.
        bar_length (int, Default: 50):
            Character length of bar. Defaults to 100.
        percent_decimals (int, Default: 1):
            Number of decimals to show in percentage. Defaults to 0.
        fill_char (str, Default: "█"): 
            Bar fill character. 
        print_end (str, Default: "\\r"): 
            End character (e.g. "\\r", "\\r\\n").
        line_number (int, Default: -1):
            The line number to print the progress bar at.
        extra_msg (str, Default: ""):
            Extra message to append to the progress bar.
        """
        self.total = total
        self.prefix = prefix
        self.suffix = suffix
        self.decimals = percent_decimals
        self.length = bar_length
        self.fill = fill_char
        self.print_end = print_end
        self.current_line = line_number
        self.end_msg = extra_msg
        self.iteration = 0
        self.has_children = False

    ############ DOERS ############
    def increment(self, extra_msg: str = ""):
        """Increments the progress bar by 1.
        
        Parameters:
        -----------
        extra_msg (str, Default: ""):
            Extra message to append to the progress bar.
        """ 
        from math import floor

        if extra_msg == "" and self.end_msg != "":
            extra_msg = self.end_msg

        if self.has_children:
            prev_cursor_line: int = self.get_current_cursor_position()[1] # need this to print line after parent finishes
            self.current_line -= 1 # this is to move the cursor to the parent bar after child has printed blank line

        self.iteration += 1
        percent = ("{0:." + str(self.decimals) + "f}").format(floor(100 * (self.iteration / float(self.total))))
        filledLength = int(self.length * self.iteration // self.total)
        bar = self.fill * filledLength + '-' * (self.length - filledLength)
        if extra_msg != "":
            extra_msg = f" - {extra_msg}"
        elif self.end_msg != "":
            extra_msg = f" - {self.end_msg}"
        self.move_cursor_to_current_line()    
        print(f'\r{self.prefix} |{bar}| {percent}% {self.suffix}{extra_msg}', end=self.print_end) 

        # Check if we've completed
        if self.iteration >= self.total:
            # if the progress bar has children, when the parent bar finishes, 
            # we need to move back to after the children before printing a new line
            if self.has_children:
                self.set_cursor_position(0, prev_cursor_line)
            
            # Print New Line on Complete
            print()
            
    def clear_line(self):
        """Clears the current line."""
        print("\033[K", end="")

    def reset_iteration(self):
        """Resets the progress bar iterations to 0."""
        self.iteration = 0
        self.increment()

    def move_cursor_to_current_line(self):
        """Sets the cursor position to the progress bars coordinate."""
        self.set_cursor_position(0, self.current_line)
        self.clear_line()

    def set_cursor_position(self, x, y):
        """Sets the cursor position to a given x and y coordinate.
        
        Parameters:
        -----------
        x (int):
            The x coordinate to set the cursor to.
        y (int):
            The y coordinate to set the cursor to.
        """
        print(f"\033[{y};{x}H", end="")

    def get_progress(self) -> float:
        """Returns the current progress of the bar progress.
        
        Returns:
        --------
        float:
            The current progress of the bar progress.
        """
        return self.iteration / self.total

    def get_percent(self) -> float:
        """Returns the current progress of the bar progress in percentage.
        
        Returns:
        --------
        float:
            The current progress of the bar progress in percentage.
        """
        return self.get_progress() * 100

    def get_bar(self) -> str:
        """Returns the current progress bar.
        
        Returns:
        --------
        str:
            The current progress bar.
        """
        percent = ("{0:." + str(self.decimals) + "f}").format(self.get_percent())
        filledLength = int(self.length * self.get_progress())
        bar = self.fill * filledLength + '-' * (self.length - filledLength)
        return f'\r{self.prefix} |{bar}| {percent}% {self.suffix}'
    
    def get_current_cursor_position(self) -> tuple:
        """Returns the current cursor position.
        
        Returns:
        --------
        tuple:
            The current cursor (x, y) position.
        """
        import shutil
        cols, lines = shutil.get_terminal_size()
        return cols, lines