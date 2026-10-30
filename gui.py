import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from engine import NormaEngine
from expander import MacroExpander

class NormaSimulatorGUI:
    """Interface Gráfica (GUI), Debugger e Inspeção (RF04)."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Simulador e Interpretador de Máquina Norma (MRN)")
        self.root.geometry("1150x720")
        self.root.minsize(950, 600)

        self.engine = NormaEngine()
        self.expander = MacroExpander()
        self.is_running = False
        self.timer_id = None

        self._setup_styles()
        self._build_gui()
        self._load_example("Soma Preservativa")

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background="#F5F6F8")
        style.configure("Header.TLabel", font=("Consolas", 14, "bold"), foreground="#1A252C", background="#F5F6F8")
        style.configure("Badge.TLabel", font=("Consolas", 10, "bold"), background="#E1E6EB", padding=5)

    def _build_gui(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill="both", expand=True)

        # Controls Header
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill="x", pady=(0, 10))

        title_lbl = ttk.Label(top_frame, text="⚙️ Máquina Norma (MRN) Simulator", style="Header.TLabel")
        title_lbl.pack(side="left", padx=(0, 15))

        self.btn_run = ttk.Button(top_frame, text="▶ Executar", command=self.run_continuous)
        self.btn_run.pack(side="left", padx=2)

        self.btn_step = ttk.Button(top_frame, text="⏭ Passo (Step)", command=self.step_once)
        self.btn_step.pack(side="left", padx=2)

        self.btn_pause = ttk.Button(top_frame, text="⏸ Pausar", command=self.pause)
        self.btn_pause.pack(side="left", padx=2)

        self.btn_reset = ttk.Button(top_frame, text="🔄 Reiniciar", command=self.reset_simulation)
        self.btn_reset.pack(side="left", padx=2)

        ttk.Label(top_frame, text="  Velocidade:").pack(side="left")
        self.speed_slider = ttk.Scale(top_frame, from_=10, to=1000, value=300, orient="horizontal", length=100)
        self.speed_slider.pack(side="left", padx=5)

        ttk.Label(top_frame, text="  Trava Ciclos:").pack(side="left")
        self.max_cycles_entry = ttk.Entry(top_frame, width=7)
        self.max_cycles_entry.insert(0, "10000")
        self.max_cycles_entry.pack(side="left", padx=2)

        # Editor & Panel
        paned = ttk.PanedWindow(main_frame, orient="horizontal")
        paned.pack(fill="both", expand=True)

        editor_frame = ttk.LabelFrame(paned, text=" Código Fonte (.norma / .txt) ", padding=5)
        paned.add(editor_frame, weight=3)

        edit_tools = ttk.Frame(editor_frame)
        edit_tools.pack(fill="x", pady=(0, 5))

        ttk.Button(edit_tools, text="📁 Abrir", command=self.open_file).pack(side="left", padx=2)
        ttk.Button(edit_tools, text="💾 Salvar", command=self.save_file).pack(side="left", padx=2)
        ttk.Button(edit_tools, text="⚡ Expandir Macros -> Primitivas", command=self.expand_macros_in_editor).pack(side="left", padx=5)

        ttk.Label(edit_tools, text="Exemplos:").pack(side="left", padx=(10, 2))
        self.example_cb = ttk.Combobox(edit_tools, values=[
            "Soma Preservativa", "Subtração Monótona", "Multiplicação",
            "Divisão Inteira e Resto", "Zerar Registrador", "Loop Primitivo Contagem"
        ], state="readonly", width=22)
        self.example_cb.pack(side="left")
        self.example_cb.bind("<<ComboboxSelected>>", lambda e: self._load_example(self.example_cb.get()))

        text_scroll = ttk.Scrollbar(editor_frame)
        text_scroll.pack(side="right", fill="y")

        self.code_editor = tk.Text(
            editor_frame, wrap="none", font=("Consolas", 11),
            yscrollcommand=text_scroll.set, bg="#FFFFFF", fg="#2C3E50", insertbackground="black"
        )
        self.code_editor.pack(fill="both", expand=True)
        text_scroll.config(command=self.code_editor.yview)

        self.code_editor.tag_configure("current_line", background="#FFEAA7", foreground="#000000")

        # Right Inspector Panel
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=2)

        status_box = ttk.LabelFrame(right_frame, text=" Inspeção do Sistema em Tempo Real ", padding=8)
        status_box.pack(fill="x", pady=(0, 5))

        self.lbl_ip = ttk.Label(status_box, text="IP: 1", style="Badge.TLabel")
        self.lbl_ip.pack(side="left", expand=True, fill="x", padx=2)

        self.lbl_cycles = ttk.Label(status_box, text="Clocks: 0", style="Badge.TLabel")
        self.lbl_cycles.pack(side="left", expand=True, fill="x", padx=2)

        reg_frame = ttk.LabelFrame(right_frame, text=" Tabela de Registradores (N) ", padding=5)
        reg_frame.pack(fill="both", expand=True, pady=(0, 5))

        self.reg_tree = ttk.Treeview(reg_frame, columns=("reg", "val"), show="headings", height=8)
        self.reg_tree.heading("reg", text="Registrador")
        self.reg_tree.heading("val", text="Valor (N)")
        self.reg_tree.column("reg", width=120, anchor="center")
        self.reg_tree.column("val", width=150, anchor="center")
        self.reg_tree.pack(fill="both", expand=True, side="left")

        tree_scroll = ttk.Scrollbar(reg_frame, command=self.reg_tree.yview)
        self.reg_tree.configure(yscrollcommand=tree_scroll.set)
        tree_scroll.pack(side="right", fill="y")

        reg_ctrl = ttk.Frame(right_frame)
        reg_ctrl.pack(fill="x", pady=(0, 5))

        ttk.Label(reg_ctrl, text="Reg:").pack(side="left")
        self.ent_reg_name = ttk.Entry(reg_ctrl, width=4)
        self.ent_reg_name.pack(side="left", padx=2)
        
        ttk.Label(reg_ctrl, text="Valor:").pack(side="left")
        self.ent_reg_val = ttk.Entry(reg_ctrl, width=6)
        self.ent_reg_val.pack(side="left", padx=2)

        ttk.Button(reg_ctrl, text="Definir", command=self.set_manual_register).pack(side="left", padx=2)

        # Log Window
        log_frame = ttk.LabelFrame(main_frame, text=" Log de Execução e Auditoria ", padding=5)
        log_frame.pack(fill="x", pady=(5, 0))

        log_scroll = ttk.Scrollbar(log_frame)
        log_scroll.pack(side="right", fill="y")

        self.log_text = tk.Text(
            log_frame, height=6, font=("Consolas", 9), bg="#1E1E1E", fg="#D4D4D4",
            yscrollcommand=log_scroll.set, wrap="word"
        )
        self.log_text.pack(fill="both", expand=True)
        log_scroll.config(command=self.log_text.yview)

    def prepare_engine(self):
        try:
            self.engine.max_cycles = int(self.max_cycles_entry.get())
        except ValueError:
            self.engine.max_cycles = 10000

        if self.engine.ip == 0 and not self.engine.code:
            code = self.code_editor.get("1.0", tk.END)
            self.engine.load_program(code)

    def update_ui_state(self):
        self.lbl_ip.config(text=f"IP: {self.engine.ip + 1}")
        self.lbl_cycles.config(text=f"Clocks: {self.engine.cycles}")

        for item in self.reg_tree.get_children():
            self.reg_tree.delete(item)

        for reg, val in sorted(self.engine.registers.items()):
            self.reg_tree.insert("", "end", values=(reg, val))

        self.code_editor.tag_remove("current_line", "1.0", tk.END)
        if 0 <= self.engine.ip < len(self.engine.code):
            line_no = self.engine.ip + 1
            self.code_editor.tag_add("current_line", f"{line_no}.0", f"{line_no}.end")
            self.code_editor.see(f"{line_no}.0")

        if self.engine.logs:
            self.log_text.delete("1.0", tk.END)
            self.log_text.insert(tk.END, "\n".join(self.engine.logs))
            self.log_text.see(tk.END)

    def step_once(self):
        self.prepare_engine()
        ok, msg = self.engine.step()
        self.update_ui_state()
        if not ok and self.engine.halted:
            messagebox.showinfo("Simulação Finalizada", msg)

    def run_continuous(self):
        self.prepare_engine()
        self.is_running = True
        self._execution_loop()

    def _execution_loop(self):
        if self.is_running and not self.engine.halted:
            ok, msg = self.engine.step()
            self.update_ui_state()
            if ok:
                delay = int(self.speed_slider.get())
                self.timer_id = self.root.after(delay, self._execution_loop)
            else:
                self.is_running = False
                messagebox.showinfo("Simulação Interrompida", msg)
        else:
            self.is_running = False

    def pause(self):
        self.is_running = False
        if self.timer_id:
            self.root.after_cancel(self.timer_id)

    def reset_simulation(self):
        self.pause()
        self.engine.reset_engine()
        code = self.code_editor.get("1.0", tk.END)
        self.engine.load_program(code)
        self.update_ui_state()

    def set_manual_register(self):
        reg = self.ent_reg_name.get().strip().upper()
        val_str = self.ent_reg_val.get().strip()
        if reg and val_str.isdigit():
            val = int(val_str)
            self.engine.set_register(reg, val)
            self.engine.initial_registers[reg] = val
            self.update_ui_state()

    def expand_macros_in_editor(self):
        code = self.code_editor.get("1.0", tk.END)
        expanded = self.expander.expand_to_primitives(code)
        self.code_editor.delete("1.0", tk.END)
        self.code_editor.insert("1.0", expanded)
        self.reset_simulation()

    def open_file(self):
        path = filedialog.askopenfilename(filetypes=[("Arquivos Norma/Texto", "*.norma *.txt"), ("Todos", "*.*")])
        if path:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.code_editor.delete("1.0", tk.END)
            self.code_editor.insert("1.0", content)
            self.reset_simulation()

    def save_file(self):
        path = filedialog.asksaveasfilename(defaultextension=".norma", filetypes=[("Norma Code", "*.norma"), ("Text", "*.txt")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.code_editor.get("1.0", tk.END))

    def _load_example(self, name):
        examples = {
            "Soma Preservativa": (
                "# RF03: Soma Preservativa A := A + B utilizando registrador auxiliar C\n"
                "SET A 5\n"
                "SET B 3\n"
                "A := A + B\n"
            ),
            "Subtração Monótona": (
                "# RF03: Subtração Monótona A := A .- B (Limitada em N)\n"
                "SET A 4\n"
                "SET B 9\n"
                "A := A .- B\n"
            ),
            "Multiplicação": (
                "# RF03: Multiplicação C := A * B por Somas Sucessivas\n"
                "SET A 4\n"
                "SET B 3\n"
                "C := A * B\n"
            ),
            "Divisão Inteira e Resto": (
                "# RF03: Divisão Inteira (Q := A div B) e Resto (R := A mod B)\n"
                "SET A 14\n"
                "SET B 3\n"
                "Q := A DIV B\n"
                "R := A MOD B\n"
            ),
            "Zerar Registrador": (
                "# RF03: Esvaziamento do registrador R ate atingir zero\n"
                "SET A 10\n"
                "ZER A\n"
            ),
            "Loop Primitivo Contagem": (
                "# RF02: Loop puramente primitivo com INC, DEC e TST\n"
                "SET A 5\n"
                "LOOP: TST A FIM DECREMENTA\n"
                "DECREMENTA: DEC A\n"
                "INC B\n"
                "TST A LOOP LOOP\n"
                "FIM: HALT\n"
            )
        }
        if name in examples:
            self.code_editor.delete("1.0", tk.END)
            self.code_editor.insert("1.0", examples[name])
            self.reset_simulation()