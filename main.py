import tkinter as tk
from gui import NormaSimulatorGUI

def main():
    root = tk.Tk()
    app = NormaSimulatorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()