import tkinter as tk
from tkinter import ttk

class GUIApp:
    def __init__(self, root):
        self.root = root
        self.root.title("数学求解器")
        
        # 工具栏
        self.toolbar = ttk.Frame(self.root, padding="5", relief=tk.RAISED, borderwidth=2)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)

        # Add toolbar buttons
        self.start_button = ttk.Button(self.toolbar, text="系统提示词")
        self.start_button.pack(side=tk.LEFT, padx=2)

        self.stop_button = ttk.Button(self.toolbar, text="加载数据集")
        self.stop_button.pack(side=tk.LEFT, padx=2)

        self.reset_button = ttk.Button(self.toolbar, text="解答")
        self.reset_button.pack(side=tk.LEFT, padx=2)

        # Create three frames below the toolbar
        self.frame1 = ttk.Frame(self.root, padding="5")
        self.frame1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.frame2 = ttk.Frame(self.root, padding="5")
        self.frame2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.frame3 = ttk.Frame(self.root, padding="5")
        self.frame3.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Add content to frames (example labels)
        ttk.Label(self.frame1, text="Frame 1").pack(pady=10)
        ttk.Label(self.frame2, text="Frame 2").pack(pady=10)
        ttk.Label(self.frame3, text="Frame 3").pack(pady=10)

        # Make the window responsive
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

if __name__ == "__main__":
    root = tk.Tk()
    app = GUIApp(root)
    root.mainloop()