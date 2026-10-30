import re

class NormaEngine:
    """Motor de execução e gerenciamento de memória da Máquina Norma (RF01 & RF02)."""
    
    def __init__(self, max_cycles=10000):
        self.registers = {}         # Alocação dinâmica em N
        self.initial_registers = {}  # Backup de valores iniciais
        self.code = []              # Lista de instruções parsadas
        self.labels = {}            # Mapeamento Rótulo -> Índice da Instrução
        self.ip = 0                 # Instruction Pointer
        self.cycles = 0             # Contador de Clocks
        self.max_cycles = max_cycles # Trava de Segurança contra loops infinitos
        self.halted = False
        self.logs = []

    def set_register(self, reg, val):
        """Aloca/Atualiza registrador com inteiros não-negativos em N (RF01)."""
        reg = reg.upper()
        self.registers[reg] = max(0, int(val))

    def get_register(self, reg):
        """Recupera o valor de um registrador (Padrão 0) (RF01)."""
        return self.registers.get(reg.upper(), 0)

    def protected_decrement(self, reg):
        """Decremento Protegido: impede underflow se R == 0 (RF01)."""
        reg = reg.upper()
        current = self.get_register(reg)
        if current > 0:
            self.registers[reg] = current - 1
        else:
            self.registers[reg] = 0

    def increment(self, reg):
        reg = reg.upper()
        self.registers[reg] = self.get_register(reg) + 1

    def reset_engine(self):
        """Reseta o estado do motor mantendo registradores pré-configurados."""
        self.registers = {k: v for k, v in self.initial_registers.items()}
        self.ip = 0
        self.cycles = 0
        self.halted = False
        self.logs = []


    def load_program(self, source_code):
        """Carrega e analisa o código-fonte."""
        self.code = []
        self.labels = {}
        self.ip = 0
        self.cycles = 0
        self.halted = False
        self.logs = []
        
        for k, v in self.initial_registers.items():
            self.registers[k] = v

        lines = source_code.split('\n')
        instr_idx = 0  # <--- Variável inicializada aqui (Isso corrige o erro da IDE)

        for line in lines:
            line_clean = line.strip()
            if not line_clean or line_clean.startswith('#') or line_clean.startswith('//'):
                continue

            # Processa múltiplos rótulos na mesma linha (ex: L1: L2: INC A)
            while ':' in line_clean and ':=' not in line_clean and '.-' not in line_clean:
                parts = line_clean.split(':', 1)
                lbl = parts[0].strip().upper()
                line_clean = parts[1].strip()
                if lbl:
                    self.labels[lbl] = instr_idx

            if line_clean:
                self.code.append({
                    'index': instr_idx,
                    'label': None, 
                    'raw': line_clean
                })
                instr_idx += 1
                
        
    def step(self):
        """Executa 1 ciclo de clock (Passo a Passo) (RF02 & RF04)."""
        if self.halted:
            return False, "Programa já finalizado."

        # Trava de Segurança Defensiva (RF04)
        if self.cycles >= self.max_cycles:
            self.halted = True
            msg = f"🛡 INTERRUPÇÃO DEFENSIVA: Limite máximo de {self.max_cycles} ciclos atingido!"
            self.logs.append(msg)
            return False, msg

        if self.ip < 0 or self.ip >= len(self.code):
            self.halted = True
            msg = "🏁 Fim do programa atingido."
            self.logs.append(msg)
            return False, msg

        # === ESTAS DUAS LINHAS PRECISAM ESTAR EXATAMENTE AQUI, FORA DOS IFs ===
        current_instr = self.code[self.ip]
        stmt = current_instr['raw']
        
        # Limpa rótulos residuais antes de executar
        while ':' in stmt and ':=' not in stmt and '.-' not in stmt:
            stmt = stmt.split(':', 1)[1].strip()

        self.cycles += 1
        
        log_msg = f"[Ciclo {self.cycles}] IP={self.ip + 1} | Executando: '{stmt}'"
        parsed = parse_statement(stmt)
        op_type = parsed['type']

        # Executor de Primitivas (RF02)
        if op_type == 'INC':
            self.increment(parsed['reg'])
            self.ip += 1

        elif op_type == 'DEC':
            self.protected_decrement(parsed['reg'])
            self.ip += 1

        elif op_type == 'TST':
            reg = parsed['reg']
            lbl_z = parsed['lbl_zero']
            lbl_nz = parsed['lbl_nonzero']
            val = self.get_register(reg)

            target = lbl_z if val == 0 else lbl_nz
            
            if target in self.labels:
                self.ip = self.labels[target]
            elif target.isdigit():
                self.ip = int(target) - 1
            elif target in ("HALT", "END", "FIM"):
                self.halted = True
                log_msg += " -> Desvio para FIM."
            else:
                self.ip += 1

        # Executor de Macros em alto nível (RF03)
        elif op_type == 'ZER':
            self.set_register(parsed['reg'], 0)
            self.ip += 1

        elif op_type == 'SET':
            self.set_register(parsed['reg'], parsed['val'])
            self.ip += 1

        elif op_type == 'ADD':
            dest, op1, op2 = parsed['dest'], parsed['op1'], parsed['op2']
            self.set_register(dest, self.get_register(op1) + self.get_register(op2))
            self.ip += 1

        elif op_type == 'SUB':
            dest, op1, op2 = parsed['dest'], parsed['op1'], parsed['op2']
            self.set_register(dest, max(0, self.get_register(op1) - self.get_register(op2)))
            self.ip += 1

        elif op_type == 'MUL':
            dest, op1, op2 = parsed['dest'], parsed['op1'], parsed['op2']
            self.set_register(dest, self.get_register(op1) * self.get_register(op2))
            self.ip += 1

        elif op_type == 'DIV':
            dest, op1, op2 = parsed['dest'], parsed['op1'], parsed['op2']
            val2 = self.get_register(op2)
            self.set_register(dest, 0 if val2 == 0 else self.get_register(op1) // val2)
            self.ip += 1

        elif op_type == 'MOD':
            dest, op1, op2 = parsed['dest'], parsed['op1'], parsed['op2']
            val2 = self.get_register(op2)
            self.set_register(dest, 0 if val2 == 0 else self.get_register(op1) % val2)
            self.ip += 1

        elif op_type == 'HALT':
            self.halted = True
            log_msg += " -> Programa Parado."

        else:
            self.ip += 1

        self.logs.append(log_msg)
        return True, log_msg
    
def parse_statement(stmt):
    """Analisador sintático para primitivas e instruções de alto nível."""
    s = stmt.strip()

    m = re.match(r'^INC\s+([A-Za-z]\w*)$', s, re.IGNORECASE)
    if m: return {'type': 'INC', 'reg': m.group(1).upper()}

    m = re.match(r'^DEC\s+([A-Za-z]\w*)$', s, re.IGNORECASE)
    if m: return {'type': 'DEC', 'reg': m.group(1).upper()}

    m = re.match(r'^TST\s+([A-Za-z]\w*)\s+(\w+)\s+(\w+)$', s, re.IGNORECASE)
    if m: return {'type': 'TST', 'reg': m.group(1).upper(), 'lbl_zero': m.group(2).upper(), 'lbl_nonzero': m.group(3).upper()}

    m = re.match(r'^ZER\s+([A-Za-z]\w*)$', s, re.IGNORECASE)
    if m: return {'type': 'ZER', 'reg': m.group(1).upper()}

    m = re.match(r'^SET\s+([A-Za-z]\w*)\s+(\d+)$', s, re.IGNORECASE)
    if m: return {'type': 'SET', 'reg': m.group(1).upper(), 'val': int(m.group(2))}

    m = re.match(r'^([A-Za-z]\w*)\s*:=\s*([A-Za-z]\w*)\s*\+\s*([A-Za-z]\w*)$', s, re.IGNORECASE)
    if m: return {'type': 'ADD', 'dest': m.group(1).upper(), 'op1': m.group(2).upper(), 'op2': m.group(3).upper()}

    m = re.match(r'^([A-Za-z]\w*)\s*:=\s*([A-Za-z]\w*)\s*\.\-\s*([A-Za-z]\w*)$', s, re.IGNORECASE)
    if m: return {'type': 'SUB', 'dest': m.group(1).upper(), 'op1': m.group(2).upper(), 'op2': m.group(3).upper()}

    m = re.match(r'^([A-Za-z]\w*)\s*:=\s*([A-Za-z]\w*)\s*\*\s*([A-Za-z]\w*)$', s, re.IGNORECASE)
    if m: return {'type': 'MUL', 'dest': m.group(1).upper(), 'op1': m.group(2).upper(), 'op2': m.group(3).upper()}

    m = re.match(r'^([A-Za-z]\w*)\s*:=\s*([A-Za-z]\w*)\s+DIV\s+([A-Za-z]\w*)$', s, re.IGNORECASE)
    if m: return {'type': 'DIV', 'dest': m.group(1).upper(), 'op1': m.group(2).upper(), 'op2': m.group(3).upper()}

    m = re.match(r'^([A-Za-z]\w*)\s*:=\s*([A-Za-z]\w*)\s+MOD\s+([A-Za-z]\w*)$', s, re.IGNORECASE)
    if m: return {'type': 'MOD', 'dest': m.group(1).upper(), 'op1': m.group(2).upper(), 'op2': m.group(3).upper()}

    if s.upper() in ('HALT', 'FIM', 'END'):
        return {'type': 'HALT'}

    return {'type': 'UNKNOWN'}