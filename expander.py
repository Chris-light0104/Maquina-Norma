from engine import parse_statement

class MacroExpander:
    """Traduz rotinas de alto nível em pseudo-instruções primitivas (RF03)."""
    
    def __init__(self):
        self.counter = 0

    def gen_lbl(self, prefix):
        self.counter += 1
        return f"{prefix}_{self.counter}"

    def _zer(self, reg):
        """Helper interno para expandir a macro ZER R em primitivas."""
        l1, l2, l3 = self.gen_lbl(f"Z_{reg}_L"), self.gen_lbl(f"Z_{reg}_D"), self.gen_lbl(f"Z_{reg}_E")
        return [
            f"{l1}: TST {reg} {l3} {l2}",
            f"{l2}: DEC {reg}",
            f"TST {reg} {l1} {l1}",
            f"{l3}: NOP"
        ]

    def _copy_preserve(self, src, dest, aux):
        """Helper interno: Copia SRC para DEST mantendo SRC intacto através do AUX."""
        out = []
        out.extend(self._zer(dest))
        out.extend(self._zer(aux))
        l1, l2, l3 = self.gen_lbl(f"CP_{src}_L"), self.gen_lbl(f"CP_{src}_D"), self.gen_lbl(f"CP_{src}_E")
        out.extend([
            f"{l1}: TST {src} {l3} {l2}",
            f"{l2}: DEC {src}",
            f"INC {dest}",
            f"INC {aux}",
            f"TST {src} {l1} {l1}",
            f"{l3}: NOP"
        ])
        l4, l5, l6 = self.gen_lbl(f"RS_{src}_L"), self.gen_lbl(f"RS_{src}_D"), self.gen_lbl(f"RS_{src}_E")
        out.extend([
            f"{l4}: TST {aux} {l6} {l5}",
            f"{l5}: DEC {aux}",
            f"INC {src}",
            f"TST {aux} {l4} {l4}",
            f"{l6}: NOP"
        ])
        return out

    def expand_to_primitives(self, source_code):
        lines = source_code.split('\n')
        out = []

        for line in lines:
            raw = line.strip()
            if not raw or raw.startswith('#') or raw.startswith('//'):
                out.append(line)
                continue

            parsed = parse_statement(raw)
            op_type = parsed['type']

            if op_type == 'ZER':
                r = parsed['reg']
                out.append(f"# --- Macro ZER {r} ---")
                out.extend(self._zer(r))

            elif op_type == 'ADD':
                a, op1, b = parsed['dest'], parsed['op1'], parsed['op2']
                c = "AUX_C"
                lz1, lz2, lz3 = self.gen_lbl("ADD_ZC_L"), self.gen_lbl("ADD_ZC_D"), self.gen_lbl("ADD_ZC_E")
                lb1, lb2, lb3 = self.gen_lbl("ADD_B_L"), self.gen_lbl("ADD_B_D"), self.gen_lbl("ADD_B_E")
                lc1, lc2, lc3 = self.gen_lbl("ADD_C_L"), self.gen_lbl("ADD_C_D"), self.gen_lbl("ADD_C_E")

                out.extend([
                    f"# --- Macro {a} := {op1} + {b} (Soma Preservativa com {c}) ---",
                    f"{lz1}: TST {c} {lz3} {lz2}",
                    f"{lz2}: DEC {c}",
                    f"TST {c} {lz1} {lz1}",
                    f"{lz3}: NOP",
                    f"{lb1}: TST {b} {lc1} {lb2}",
                    f"{lb2}: DEC {b}",
                    f"INC {a}",
                    f"INC {c}",
                    f"TST {b} {lb1} {lb1}",
                    f"{lc1}: TST {c} {lc3} {lc2}",
                    f"{lc2}: DEC {c}",
                    f"INC {b}",
                    f"TST {c} {lc1} {lc1}",
                    f"{lc3}: NOP"
                ])

            elif op_type == 'SUB':
                a, op1, b = parsed['dest'], parsed['op1'], parsed['op2']
                c = "AUX_C"
                lz1, lz2, lz3 = self.gen_lbl("SUB_ZC_L"), self.gen_lbl("SUB_ZC_D"), self.gen_lbl("SUB_ZC_E")
                lb1, lb2, lb3 = self.gen_lbl("SUB_B_L"), self.gen_lbl("SUB_B_D"), self.gen_lbl("SUB_B_E")
                lc1, lc2, lc3 = self.gen_lbl("SUB_C_L"), self.gen_lbl("SUB_C_D"), self.gen_lbl("SUB_C_E")

                out.extend([
                    f"# --- Macro {a} := {op1} .- {b} (Subtração Monótona com {c}) ---",
                    f"{lz1}: TST {c} {lz3} {lz2}",
                    f"{lz2}: DEC {c}",
                    f"TST {c} {lz1} {lz1}",
                    f"{lz3}: NOP",
                    f"{lb1}: TST {b} {lc1} {lb2}",
                    f"{lb2}: DEC {b}",
                    f"DEC {a}",
                    f"INC {c}",
                    f"TST {b} {lb1} {lb1}",
                    f"{lc1}: TST {c} {lc3} {lc2}",
                    f"{lc2}: DEC {c}",
                    f"INC {b}",
                    f"TST {c} {lc1} {lc1}",
                    f"{lc3}: NOP"
                ])

            elif op_type == 'MUL':
                a, op1, b = parsed['dest'], parsed['op1'], parsed['op2']
                out.append(f"# --- Macro {a} := {op1} * {b} (Multiplicação por Somas Sucessivas) ---")
                out.extend(self._zer(a))
                
                # Copia op1 para AUX_A e restaura op1 intacto
                out.extend(self._copy_preserve(op1, "AUX_A", "AUX_A2"))
                
                l_m1, l_m2, l_m3 = self.gen_lbl("MUL_L"), self.gen_lbl("MUL_D"), self.gen_lbl("MUL_E")
                out.extend([
                    f"{l_m1}: TST AUX_A {l_m3} {l_m2}",
                    f"{l_m2}: DEC AUX_A"
                ])
                
                # Soma 'b' em 'a', preservando 'b' em AUX_B
                l_b1, l_b2, l_b3 = self.gen_lbl("MB_L"), self.gen_lbl("MB_D"), self.gen_lbl("MB_E")
                l_r1, l_r2, l_r3 = self.gen_lbl("MR_L"), self.gen_lbl("MR_D"), self.gen_lbl("MR_E")
                
                out.extend(self._zer("AUX_B"))
                out.extend([
                    f"{l_b1}: TST {b} {l_b3} {l_b2}",
                    f"{l_b2}: DEC {b}",
                    f"INC {a}",
                    f"INC AUX_B",
                    f"TST {b} {l_b1} {l_b1}",
                    f"{l_b3}: NOP",
                    f"{l_r1}: TST AUX_B {l_r3} {l_r2}",
                    f"{l_r2}: DEC AUX_B",
                    f"INC {b}",
                    f"TST AUX_B {l_r1} {l_r1}",
                    f"{l_r3}: NOP",
                    f"TST AUX_A {l_m1} {l_m1}",
                    f"{l_m3}: NOP"
                ])

            elif op_type in ('DIV', 'MOD'):
                a, op1, b = parsed['dest'], parsed['op1'], parsed['op2']
                op_name = "Divisão Inteira" if op_type == 'DIV' else "Resto da Divisão"
                op_sign = "DIV" if op_type == 'DIV' else "MOD"
                out.append(f"# --- Macro {a} := {op1} {op_sign} {b} ({op_name} via Subtração Lógica) ---")
                
                out.extend(self._zer("Q_TEMP"))
                out.extend(self._zer("R_TEMP"))
                
                # Armazena cópia de A em AUX_A para o loop principal
                out.extend(self._copy_preserve(op1, "AUX_A", "AUX_A2"))
                
                l_m1, l_m2, l_m3 = self.gen_lbl("DIV_L"), self.gen_lbl("DIV_D"), self.gen_lbl("DIV_E")
                out.extend([
                    f"{l_m1}: TST AUX_A {l_m3} {l_m2}",
                    f"{l_m2}: DEC AUX_A",
                    f"INC R_TEMP"
                ])
                
                # Check R_TEMP == B (Se forem iguais, incrementa o quociente e zera o resto)
                out.extend(self._copy_preserve("R_TEMP", "AUX_R", "AUX_R2"))
                out.extend(self._copy_preserve(b, "AUX_B", "AUX_B2"))
                
                l_c1, l_rnz, l_rz = self.gen_lbl("CMP_L"), self.gen_lbl("CMP_RNZ"), self.gen_lbl("CMP_RZ")
                l_bnz, l_bz = self.gen_lbl("CMP_BNZ"), self.gen_lbl("CMP_BZ")
                l_eq, l_neq, l_end = self.gen_lbl("CMP_EQ"), self.gen_lbl("CMP_NEQ"), self.gen_lbl("CMP_END")
                
                out.extend([
                    f"{l_c1}: TST AUX_R {l_rz} {l_rnz}",
                    f"{l_rnz}: TST AUX_B {l_bz} {l_bnz}",
                    f"{l_bnz}: DEC AUX_R",
                    f"DEC AUX_B",
                    f"TST AUX_R {l_c1} {l_c1}",
                    f"{l_bz}: TST AUX_R {l_neq} {l_neq}",
                    f"{l_rz}: TST AUX_B {l_eq} {l_neq}",
                    f"{l_eq}: NOP"
                ])
                
                # Condição de Igualdade atingida (Resto == Divisor)
                out.extend(self._zer("R_TEMP"))
                out.extend([
                    f"INC Q_TEMP",
                    f"TST AUX_R {l_end} {l_end}",
                    f"{l_neq}: NOP",
                    f"{l_end}: NOP",
                    f"TST AUX_A {l_m1} {l_m1}",
                    f"{l_m3}: NOP"
                ])
                
                # Transfere para o registrador final o resultado desejado (Q ou R)
                out.extend(self._zer(a))
                src_temp = "Q_TEMP" if op_type == 'DIV' else "R_TEMP"
                
                l_t1, l_t2, l_t3 = self.gen_lbl("TR_L"), self.gen_lbl("TR_D"), self.gen_lbl("TR_E")
                out.extend([
                    f"{l_t1}: TST {src_temp} {l_t3} {l_t2}",
                    f"{l_t2}: DEC {src_temp}",
                    f"INC {a}",
                    f"TST {src_temp} {l_t1} {l_t1}",
                    f"{l_t3}: NOP"
                ])

            else:
                out.append(line)

        return '\n'.join(out)