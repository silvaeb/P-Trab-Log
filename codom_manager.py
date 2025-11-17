import pandas as pd
import os

class CODOMManager:
    def __init__(self):
        self.codom_data = {}  # {CODOM: {descricao, sigla_qr, sigla_qs, codug_qr, codug_qs}}
        self.all_options = []  # Todas as opções para pesquisa
        self.carregar_dados_codom()
    
    def carregar_dados_codom(self):
        """Carrega os dados do CODOM do arquivo Excel usando a DESCRIÇÃO como principal"""
        try:
            if os.path.exists('CODOM.xlsx'):
                print("📂 Carregando dados do CODOM.xlsx...")
                df = pd.read_excel('CODOM.xlsx', sheet_name='Cod_OM_UG')
                print(f"📊 Colunas encontradas: {list(df.columns)}")
                print(f"📊 Total de registros: {len(df)}")
                
                # Mapear colunas (DAR PRIORIDADE À DESCRIÇÃO)
                col_map = {}
                for col in df.columns:
                    col_lower = col.lower().strip()
                    if 'codom' in col_lower:
                        col_map['codom'] = col
                    elif 'descrição' in col_lower or 'descricao' in col_lower:
                        col_map['descricao'] = col
                    elif 'sigla om vinc qr' in col_lower:
                        col_map['sigla_qr'] = col
                    elif 'sigla om vinc qs' in col_lower:
                        col_map['sigla_qs'] = col
                    elif 'codug_qr' in col_lower or ('codug' in col_lower and 'qr' in col_lower):
                        col_map['codug_qr'] = col
                    elif 'codug_qs' in col_lower or ('codug' in col_lower and 'qs' in col_lower):
                        col_map['codug_qs'] = col
                
                print(f"🔍 Mapeamento de colunas: {col_map}")
                
                # Verificar se temos todas as colunas necessárias
                colunas_necessarias = ['codom', 'descricao']
                for coluna in colunas_necessarias:
                    if coluna not in col_map:
                        print(f"❌ Coluna {coluna} não encontrada no arquivo Excel")
                        return False
                
                # COLUNAS OPCIONAIS - definir fallbacks
                if 'sigla_qr' not in col_map:
                    col_map['sigla_qr'] = col_map['descricao']
                if 'sigla_qs' not in col_map:
                    col_map['sigla_qs'] = col_map['descricao']
                if 'codug_qr' not in col_map:
                    col_map['codug_qr'] = None
                if 'codug_qs' not in col_map:
                    col_map['codug_qs'] = None
                
                for index, row in df.iterrows():
                    try:
                        codom = str(row[col_map['codom']]).strip()
                        
                        # Pular linhas vazias
                        if not codom or codom == 'nan' or codom == 'None':
                            continue
                            
                        # USAR A DESCRIÇÃO COMO PRINCIPAL (não a sigla)
                        descricao = str(row[col_map['descricao']]).strip() if pd.notna(row[col_map['descricao']]) else ""
                        
                        # CORREÇÃO: Extrair SIGLA para QR e QS com fallbacks
                        sigla_qr = ""
                        sigla_qs = ""
                        
                        if col_map['sigla_qr'] and pd.notna(row[col_map['sigla_qr']]):
                            sigla_qr = str(row[col_map['sigla_qr']]).strip()
                        else:
                            sigla_qr = descricao  # Fallback
                            
                        if col_map['sigla_qs'] and pd.notna(row[col_map['sigla_qs']]):
                            sigla_qs = str(row[col_map['sigla_qs']]).strip()
                        else:
                            sigla_qs = descricao  # Fallback
                        
                        # CODUG - CORREÇÃO com fallbacks
                        codug_qr = ""
                        codug_qs = ""
                        
                        if col_map['codug_qr'] and pd.notna(row[col_map['codug_qr']]):
                            codug_qr = str(row[col_map['codug_qr']]).strip()
                            # Remover caracteres não numéricos e limitar a 6 dígitos
                            codug_qr = ''.join(filter(str.isdigit, codug_qr))[:6]
                        else:
                            codug_qr = f"160{index+1:03d}"  # Fallback
                            
                        if col_map['codug_qs'] and pd.notna(row[col_map['codug_qs']]):
                            codug_qs = str(row[col_map['codug_qs']]).strip()
                            # Remover caracteres não numéricos e limitar a 6 dígitos
                            codug_qs = ''.join(filter(str.isdigit, codug_qs))[:6]
                        else:
                            codug_qs = f"160{index+1:03d}"  # Fallback
                        
                        # Garantir que CODUG comece com 160
                        if not codug_qr.startswith('160'):
                            codug_qr = f"160{index+1:03d}"
                        if not codug_qs.startswith('160'):
                            codug_qs = f"160{index+1:03d}"
                        
                        self.codom_data[codom] = {
                            'descricao': descricao,
                            'sigla_qr': sigla_qr,
                            'sigla_qs': sigla_qs,
                            'codug_qr': codug_qr,
                            'codug_qs': codug_qs
                        }
                        
                    except Exception as e:
                        print(f"❌ Erro na linha {index}: {e}")
                        continue
                
                # Criar lista de opções para o Spinner
                self.all_options = self._criar_lista_opcoes()
                print(f"✅ Dados CODOM carregados: {len(self.codom_data)} registros")
                print(f"📋 Total de opções: {len(self.all_options)}")
                
                return True
                
            else:
                print("⚠️  Arquivo CODOM.xlsx não encontrado. Usando dados padrão.")
                self.carregar_dados_padrao()
                return True
                
        except Exception as e:
            print(f"❌ Erro ao carregar CODOM.xlsx: {e}")
            import traceback
            print(f"🔍 Detalhes: {traceback.format_exc()}")
            self.carregar_dados_padrao()
            return True
    
    def _criar_lista_opcoes(self):
        """Cria a lista de opções para o Spinner"""
        opcoes = ["Selecione o CODOM"]
        for codom, dados in self.codom_data.items():
            # Usar formato: CODOM - Descrição (ao invés de sigla)
            opcoes.append(f"{codom} - {dados['descricao']}")
        return sorted(opcoes, key=lambda x: x.lower())
    
    def carregar_dados_padrao(self):
        """Carrega dados padrão caso o arquivo Excel não exista"""
        print("🔄 Carregando dados padrão do CODOM...")
        
        dados_padrao = {
            "6122": {
                "descricao": "40º BI",
                "sigla_qr": "40º BI",
                "sigla_qs": "40º BI", 
                "codug_qr": "160041",
                "codug_qs": "160047"
            },
            "1503": {
                "descricao": "23º BC",
                "sigla_qr": "23º BC",
                "sigla_qs": "23º BC",
                "codug_qr": "160045", 
                "codug_qs": "160047"
            },
            "1438": {
                "descricao": "Ba Adm / Gu Fortaleza",
                "sigla_qr": "Ba Adm / Gu Fortaleza",
                "sigla_qs": "Ba Adm / Gu Fortaleza",
                "codug_qr": "160045",
                "codug_qs": "160047"
            }
        }
        
        self.codom_data = dados_padrao
        self.all_options = self._criar_lista_opcoes()
        print("✅ Dados CODOM padrão carregados")
    
    def get_all_options(self):
        """Retorna todas as opções disponíveis"""
        return self.all_options
    
    def search_options(self, termo):
        """Pesquisa opções por CODOM ou descrição da OM"""
        if not termo:
            return self.all_options
        
        termo = termo.lower().strip()
        resultados = ["Selecione o CODOM"]
        
        for opcao in self.all_options[1:]:  # Pular o primeiro item "Selecione o CODOM"
            if termo in opcao.lower():
                resultados.append(opcao)
        
        return resultados if len(resultados) > 1 else ["Selecione o CODOM", "Nenhum resultado encontrado"]
    
    def extract_codom_from_selection(self, selection):
        """Extrai apenas o código CODOM da seleção do Spinner"""
        if selection and ' - ' in selection:
            return selection.split(' - ')[0].strip()
        return selection.strip() if selection else ""
    
    def get_sigla_for_tipo(self, codom_selection, tipo):
        """Retorna a SIGLA da OM baseada no CODOM e tipo (QR/QS/Ração) - CORRIGIDO"""
        if not codom_selection or codom_selection == "Selecione o CODOM":
            return ""
            
        codom = self.extract_codom_from_selection(codom_selection)
        if codom in self.codom_data:
            # Para ração operacional, usar QR como base
            if 'Ração Operacional' in str(tipo):
                return self.codom_data[codom]['sigla_qr']
            elif tipo == 'QR':
                return self.codom_data[codom]['sigla_qr']
            else:  # QS
                return self.codom_data[codom]['sigla_qs']
        return ""
    
    def get_codug_for_tipo(self, codom_selection, tipo):
        """Retorna o CODUG correto baseado no CODOM e tipo (QR/QS/Ração) - CORRIGIDO"""
        if not codom_selection or codom_selection == "Selecione o CODOM":
            return ""
            
        codom = self.extract_codom_from_selection(codom_selection)
        if codom in self.codom_data:
            # Para ração operacional, usar QR como base
            if 'Ração Operacional' in str(tipo):
                return self.codom_data[codom]['codug_qr']
            elif tipo == 'QR':
                return self.codom_data[codom]['codug_qr']
            else:  # QS
                return self.codom_data[codom]['codug_qs']
        return ""
    
    def get_descricao_completa(self, codom):
        """Retorna a descrição completa para exibição no PDF"""
        if not codom or codom == "Selecione o CODOM":
            return ""
            
        codom_limpo = self.extract_codom_from_selection(codom) if ' - ' in str(codom) else codom
        if codom_limpo in self.codom_data:
            descricao = self.codom_data[codom_limpo]['descricao']
            return f"{codom_limpo} - {descricao}"
        return f"{codom_limpo} - OM Não Identificada"
    
    def get_om_from_codom(self, codom_selection):
        """Retorna a descrição da OM baseada no CODOM selecionado"""
        if not codom_selection or codom_selection == "Selecione o CODOM":
            return ""
            
        codom = self.extract_codom_from_selection(codom_selection)
        if codom in self.codom_data:
            return self.codom_data[codom]['descricao']
        return ""

# Instância global do gerenciador de CODOM
codom_manager = CODOMManager()