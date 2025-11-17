import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import secrets

class HomologacaoSystem:
    def __init__(self):
        self.homologacao_file = 'homologacao_data.json'
        self.pdf_uploads_file = 'pdf_uploads.json'
        self.load_data()
    
    def load_data(self):
        """Carrega os dados de homologação"""
        try:
            if os.path.exists(self.homologacao_file):
                with open(self.homologacao_file, 'r', encoding='utf-8') as f:
                    self.homologacao_data = json.load(f)
            else:
                self.homologacao_data = {}
                self.save_data()
            
            if os.path.exists(self.pdf_uploads_file):
                with open(self.pdf_uploads_file, 'r', encoding='utf-8') as f:
                    self.pdf_uploads = json.load(f)
            else:
                self.pdf_uploads = {}
                self.save_pdf_uploads()
                
        except Exception as e:
            st.error(f"Erro ao carregar dados de homologação: {e}")
            self.homologacao_data = {}
            self.pdf_uploads = {}
    
    def save_data(self):
        """Salva os dados de homologação"""
        try:
            with open(self.homologacao_file, 'w', encoding='utf-8') as f:
                json.dump(self.homologacao_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            st.error(f"Erro ao salvar dados de homologação: {e}")
    
    def save_pdf_uploads(self):
        """Salva os uploads de PDF"""
        try:
            with open(self.pdf_uploads_file, 'w', encoding='utf-8') as f:
                json.dump(self.pdf_uploads, f, ensure_ascii=False, indent=2)
        except Exception as e:
            st.error(f"Erro ao salvar uploads de PDF: {e}")
    
    def register_pdf_upload(self, pdf_file, user_info, dados_operacao, valor_operacao=0):
        """Registra um upload de PDF para homologação"""
        pdf_id = f"PDF_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(4)}"
        
        # Garantir que tipo_operacao tenha um valor padrão
        tipo_operacao = dados_operacao.get('tipo', '1')  # 1=Emprego, 2=Preparo
        
        self.pdf_uploads[pdf_id] = {
            'nome_arquivo': pdf_file.name,
            'data_upload': datetime.now().isoformat(),
            'usuario': user_info['nome'],
            'cpf_usuario': list(user_info.keys())[0] if isinstance(user_info, dict) else 'N/A',
            'posto_usuario': user_info['posto'],
            'om_usuario': user_info['om'],
            'dados_operacao': dados_operacao,
            'valor_operacao': float(valor_operacao),
            'status': 'pendente',
            'data_homologacao': None,
            'homologador': None,
            'justificativa': None,
            'tipo_operacao': tipo_operacao,  # Garantir que sempre existe
            'numero_ptrab': None  # Será preenchido na homologação
        }
        
        self.save_pdf_uploads()
        return pdf_id
    
    def get_pdfs_pendentes(self):
        """Retorna todos os PDFs pendentes de homologação"""
        return {k: v for k, v in self.pdf_uploads.items() if v['status'] == 'pendente'}
    
    def get_pdfs_aprovados(self):
        """Retorna todos os PDFs aprovados"""
        return {k: v for k, v in self.pdf_uploads.items() if v['status'] == 'aprovado'}
    
    def get_pdfs_rejeitados(self):
        """Retorna todos os PDFs rejeitados"""
        return {k: v for k, v in self.pdf_uploads.items() if v['status'] == 'rejeitado'}
    
    def homologar_pdf(self, pdf_id, homologador, status, justificativa=None):
        """Realiza a homologação de um PDF integrado com o saldo - CORRIGIDO"""
        if pdf_id not in self.pdf_uploads:
            return False, "PDF não encontrado"
        
        pdf_data = self.pdf_uploads[pdf_id]
        status_anterior = pdf_data['status']
        
        # Obter tipo_operacao com fallback seguro
        tipo_operacao = pdf_data.get('tipo_operacao', '1')  # Default para EMPREGO se não existir
        numero_ptrab = pdf_data.get('numero_ptrab', '')
        
        # Se estava aprovado e agora está sendo rejeitado, estornar valor
        if status_anterior == 'aprovado' and status == 'rejeitado':
            if tipo_operacao == '2':  # Preparo
                try:
                    from saldo_manager import saldo_manager
                    if numero_ptrab:
                        success, msg = saldo_manager.estornar_valor_por_ptrab(numero_ptrab, homologador)
                        if not success:
                            return False, f"Erro no estorno: {msg}"
                except ImportError as e:
                    return False, f"Erro ao acessar sistema de saldo: {e}"
        
        # Se está sendo aprovado agora, abater valor (apenas para preparo)
        if status == 'aprovado' and tipo_operacao == '2':  # Preparo
            try:
                from saldo_manager import saldo_manager
                valor_operacao = pdf_data.get('valor_operacao', 0)
                descricao = f"P Trab: {numero_ptrab} - {pdf_data['dados_operacao'].get('nome_operacao', 'N/A')}"
                if numero_ptrab:
                    success, msg = saldo_manager.abater_valor_por_ptrab(numero_ptrab, valor_operacao, descricao, homologador)
                    if not success:
                        return False, f"Erro no abatimento: {msg}"
            except ImportError as e:
                return False, f"Erro ao acessar sistema de saldo: {e}"
        
        # Atualizar status do PDF
        self.pdf_uploads[pdf_id]['status'] = status
        self.pdf_uploads[pdf_id]['data_homologacao'] = datetime.now().isoformat()
        self.pdf_uploads[pdf_id]['homologador'] = homologador
        self.pdf_uploads[pdf_id]['justificativa'] = justificativa
        
        # Se aprovado, carregar na planilha NC Auditor
        if status == 'aprovado':
            self.carregar_nc_auditor(pdf_id)
        
        self.save_pdf_uploads()
        return True, f"PDF {status} com sucesso"
    
    def excluir_pdf(self, pdf_id, homologador):
        """Exclui um PDF e estorna o valor se estiver aprovado - CORRIGIDO"""
        if pdf_id not in self.pdf_uploads:
            return False, "PDF não encontrado"
        
        pdf_data = self.pdf_uploads[pdf_id]
        
        # Obter tipo_operacao com fallback seguro
        tipo_operacao = pdf_data.get('tipo_operacao', '1')
        numero_ptrab = pdf_data.get('numero_ptrab', '')
        
        # Se estava aprovado, estornar valor (apenas para preparo)
        if pdf_data['status'] == 'aprovado' and tipo_operacao == '2':
            try:
                from saldo_manager import saldo_manager
                if numero_ptrab:
                    success, msg = saldo_manager.estornar_valor_por_ptrab(numero_ptrab, homologador)
                    if not success:
                        return False, f"Erro no estorno: {msg}"
            except ImportError as e:
                return False, f"Erro ao acessar sistema de saldo: {e}"
        
        # Remover o PDF
        del self.pdf_uploads[pdf_id]
        self.save_pdf_uploads()
        
        return True, "PDF excluído com sucesso"
    
    def carregar_nc_auditor(self, pdf_id):
        """Carrega os dados do PDF aprovado na planilha NC Auditor - ATUALIZADA"""
        try:
            pdf_data = self.pdf_uploads[pdf_id]
            
            nc_auditor_file = 'nc_auditor.xlsx'
            
            # Criar ou carregar planilha existente
            if os.path.exists(nc_auditor_file):
                df = pd.read_excel(nc_auditor_file)
            else:
                df = pd.DataFrame(columns=[
                    'ID_PDF', 'Numero_PTrab', 'Data_Homologacao', 'Usuario', 'OM_Usuario',
                    'Nome_Operacao', 'Periodo', 'Local', 'Solicitante',
                    'Efetivo_Total', 'Valor_Operacao', 'Status', 'Tipo_Operacao', 'Homologador'
                ])
            
            # Adicionar nova linha
            nova_linha = {
                'ID_PDF': pdf_id,
                'Numero_PTrab': pdf_data.get('numero_ptrab', ''),
                'Data_Homologacao': pdf_data['data_homologacao'],
                'Usuario': pdf_data['usuario'],
                'OM_Usuario': pdf_data['om_usuario'],
                'Nome_Operacao': pdf_data['dados_operacao'].get('nome_operacao', ''),
                'Periodo': pdf_data['dados_operacao'].get('periodo', ''),
                'Local': pdf_data['dados_operacao'].get('local', ''),
                'Solicitante': pdf_data['dados_operacao'].get('solicitante', ''),
                'Efetivo_Total': pdf_data['dados_operacao'].get('efetivo_total', ''),
                'Valor_Operacao': pdf_data['valor_operacao'],
                'Status': 'APROVADO',
                'Tipo_Operacao': 'PREPARO' if pdf_data.get('tipo_operacao', '1') == '2' else 'EMPREGO',
                'Homologador': pdf_data['homologador']
            }
            
            df = pd.concat([df, pd.DataFrame([nova_linha])], ignore_index=True)
            df.to_excel(nc_auditor_file, index=False)
            
            return True
            
        except Exception as e:
            st.error(f"Erro ao carregar na planilha NC Auditor: {e}")
            return False

# Instância global do sistema de homologação
homologacao_system = HomologacaoSystem()